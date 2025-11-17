// frontend/src/CandidateView.jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { MessageSquare, Plus, X, Clock, Loader2, GitBranch, ExternalLink, CheckCircle } from 'lucide-react'
import axios from 'axios'
import * as monaco from 'monaco-editor'

const API_URL = '/api'

export default function CandidateView() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [diffContent, setDiffContent] = useState('')
  const [comments, setComments] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedLine, setSelectedLine] = useState(null)
  const [newComment, setNewComment] = useState({
    file: 'main.py',
    line_range: '',
    type: 'bug',
    severity: 'medium',
    text: ''
  })
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [status, setStatus] = useState('')
  
  const [isBlinking, setIsBlinking] = useState(false)
  const [notificationShown, setNotificationShown] = useState(false)
  const [isMarkingReady, setIsMarkingReady] = useState(false)
  const editorRef = useRef(null)
  const audioContextRef = useRef(null)
  const tickIntervalRef = useRef(null)
  const exitTimeoutRef = useRef(null)

  // Загрузка сессии
  useEffect(() => {
    if (token) {
      loadSession()
    }
  }, [token])

  const loadSession = async () => {
    setIsLoading(true)
    try {
      const sessionRes = await axios.get(`${API_URL}/candidate/sessions/${token}`)
      const sessionData = sessionRes.data
      
      setSession(sessionData)
      
      // Если Gitea включена, но PR не создан - загружаем только сессию (без diff)
      // Для случая без Gitea загружаем diff
      if (!sessionData.gitea?.enabled) {
        const diffRes = await axios.get(`${API_URL}/candidate/sessions/${token}/diff`, { responseType: 'text' })
          .catch(() => ({ data: '# No diff available' }))
        setDiffContent(diffRes.data)
      }
      
      setComments(sessionData.comments || [])
      
      // Сохраняем expires_at для таймера
      if (sessionData.expires_at) {
        localStorage.setItem(`session_${sessionData.session_id}`, JSON.stringify({
          expires_at: sessionData.expires_at,
          created_at: sessionData.created_at
        }))
      }
    } catch (err) {
      setStatus('Ошибка загрузки сессии. Проверьте токен.')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Обновление комментариев
  const addComment = async () => {
    if (!newComment.text.trim() || !newComment.line_range) {
      setStatus('Заполните все поля')
      return
    }

    try {
      await axios.post(`${API_URL}/candidate/sessions/${token}/comments`, newComment)
      setSelectedLine(null)
      setNewComment({ ...newComment, text: '', line_range: '' })
      await loadSession()
      setStatus('Комментарий добавлен')
    } catch (err) {
      console.error(err)
      setStatus('Ошибка добавления комментария')
    }
  }

  // Отметить готовность
  const markReady = async () => {
    if (!confirm('Вы уверены, что завершили code review? После этого вы не сможете добавлять комментарии.')) {
      return
    }

    setIsMarkingReady(true)
    try {
      const res = await axios.post(`${API_URL}/candidate/sessions/${token}/ready`)
      await loadSession()
      setStatus('Готовность отмечена! Ревьюер будет уведомлён.')
    } catch (err) {
      console.error(err)
      setStatus('Ошибка при отметке готовности')
    } finally {
      setIsMarkingReady(false)
    }
  }

  // Автоматически открываем Gitea и таймер при первой загрузке (если Gitea включена)
  useEffect(() => {
    if (!session?.gitea?.enabled || !session?.gitea?.pr_url || !token) return
    
    const timerOpened = sessionStorage.getItem(`timer-opened-${token}`)
    const giteaOpened = sessionStorage.getItem(`gitea-opened-${token}`)
    
    // Открываем Gitea в новой вкладке (только один раз)
    if (!giteaOpened) {
      const giteaWindow = window.open(session.gitea.pr_url, '_blank')
      if (giteaWindow) {
        sessionStorage.setItem(`gitea-opened-${token}`, 'true')
      }
    }
    
    // Открываем таймер в popup (только один раз, если пользователь не закрыл его ранее)
    if (!timerOpened) {
      setTimeout(() => {
        const timerUrl = `/timer/${token}`
        const timerWindow = window.open(
          timerUrl,
          'timer-widget',
          'width=400,height=320,resizable=yes,scrollbars=no,status=no,toolbar=no,menubar=no,location=no'
        )
        if (timerWindow) {
          sessionStorage.setItem(`timer-opened-${token}`, 'true')
          timerWindow.focus()
          
          // Отслеживаем закрытие окна таймера
          const checkClosed = setInterval(() => {
            if (timerWindow.closed) {
              sessionStorage.removeItem(`timer-opened-${token}`)
              clearInterval(checkClosed)
            }
          }, 1000)
        }
      }, 500) // Небольшая задержка, чтобы не блокировать основной интерфейс
    }
  }, [token, session?.gitea?.enabled, session?.gitea?.pr_url])

  // Таймер сессии
  useEffect(() => {
    if (!session?.expires_at) return

    const updateTimer = () => {
      const expiresAt = session.expires_at
      const expiresAtUTC = expiresAt.endsWith('Z') || expiresAt.includes('+') || expiresAt.includes('-') 
        ? expiresAt 
        : expiresAt + 'Z'
      const end = new Date(expiresAtUTC).getTime()
      const now = Date.now()
      const diff = Math.max(0, end - now)

      const hours = Math.floor(diff / 3600000)
      const minutes = Math.floor((diff % 3600000) / 60000)
      const seconds = Math.floor((diff % 60000) / 1000)
      const timeStr = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`

      const timerEl = document.getElementById('candidate-timer')
      if (timerEl) timerEl.textContent = timeStr

      const progressEl = document.getElementById('candidate-progress')
      if (progressEl) {
        const total = 2 * 60 * 60 * 1000 // 2 часа в миллисекундах
        const percent = (diff / total) * 100
        progressEl.style.width = `${Math.max(0, percent)}%`
        
        // Цвет по оставшемуся времени (как в Reviewer Dashboard)
        if (percent < 15) {
          progressEl.style.background = '#e74c3c'
        } else if (percent < 40) {
          progressEl.style.background = '#f39c12'
        } else {
          progressEl.style.background = '#27ae60'
        }
      }

      // Мигание при < 5 минут
      if (diff < 5 * 60000 && diff > 0) {
        setIsBlinking(true)
      } else {
        setIsBlinking(false)
      }

      // Звук "тик-так" при < 1 минуте
      if (diff < 60000 && diff > 0 && diff % 1000 < 100) {
        playTickSound()
      }

      // Уведомление при < 10 минут
      if (diff < 10 * 60000 && diff > 0 && !notificationShown) {
        showBrowserNotification('Осталось менее 10 минут до окончания сессии!')
        setNotificationShown(true)
      }

      // Выход при истечении
      if (diff === 0) {
        if (exitTimeoutRef.current) {
          clearTimeout(exitTimeoutRef.current)
        }
        exitTimeoutRef.current = setTimeout(() => {
          setStatus('Сессия истекла')
          alert('Сессия истекла. Пожалуйста, обратитесь к проверяющему.')
        }, 1000)
      } else {
        if (exitTimeoutRef.current) {
          clearTimeout(exitTimeoutRef.current)
          exitTimeoutRef.current = null
        }
      }
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    tickIntervalRef.current = interval

    return () => {
      clearInterval(interval)
      if (exitTimeoutRef.current) {
        clearTimeout(exitTimeoutRef.current)
      }
    }
  }, [session?.expires_at, notificationShown])

  const playTickSound = useCallback(() => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      }
      const ctx = audioContextRef.current
      const oscillator = ctx.createOscillator()
      const gainNode = ctx.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(ctx.destination)
      
      oscillator.frequency.value = 800
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.1, ctx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1)
      
      oscillator.start(ctx.currentTime)
      oscillator.stop(ctx.currentTime + 0.1)
    } catch (err) {
      // Игнорируем ошибки звука
    }
  }, [])

  const showBrowserNotification = useCallback((message) => {
    if (!('Notification' in window)) return
    
    if (Notification.permission === 'granted') {
      new Notification('Code Review Platform', {
        body: message,
        icon: '/vite.svg'
      })
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification('Code Review Platform', {
            body: message,
            icon: '/vite.svg'
          })
        }
      })
    }
  }, [])

  // Декорации для комментариев
  useEffect(() => {
    if (!editorRef.current) return
    const decs = comments.map(c => {
      const [s, e] = c.line_range.split('-').map(Number)
      return {
        range: new monaco.Range(s, 1, e ?? s, 1),
        options: {
          isWholeLine: true,
          className: 'bg-yellow-200 dark:bg-yellow-900 opacity-30',
          hoverMessage: { value: `**${c.type}**: ${c.text}` }
        }
      }
    })
    editorRef.current.deltaDecorations([], decs)
  }, [comments])

  const handleEditorDidMount = (editor) => {
    editorRef.current = editor
    editor.onMouseDown(e => {
      // Не позволяем выбирать строки, если кандидат уже отметил готовность
      if (session?.candidate_ready_at) {
        return
      }
      if (e.target.type === 2) {
        const line = e.target.position.lineNumber
        setSelectedLine(line)
        setNewComment(p => ({ ...p, line_range: `${line}-${line}` }))
        setSidebarOpen(true)
      }
    })
  }

  const jumpToLine = (range) => {
    const [s] = range.split('-').map(Number)
    editorRef.current?.revealLineInCenter(s)
    editorRef.current?.setPosition({ lineNumber: s, column: 1 })
  }

  if (isLoading) {
    return (
      <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Loader2 size={32} className="animate-spin" />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>Сессия не найдена</h2>
          <p style={{ color: '#666' }}>Проверьте токен доступа</p>
        </div>
      </div>
    )
  }

  // Если Gitea включена и PR создан - показываем страницу с прогресс-баром и автоматически открываем Gitea
  if (session.gitea?.enabled && session.gitea?.pr_url) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100vh',
        overflow: 'hidden',
        background: '#f5f5f5'
      }}>
        {/* HEADER С ПРОГРЕСС-БАРОМ */}
        <header style={{
          background: 'white',
          borderBottom: '1px solid #e0e0e0',
          padding: '12px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
          zIndex: 1000,
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '16px', fontWeight: '600' }}>Code Review Session</span>
            <span style={{ fontSize: '14px', color: '#666' }}> • {session.candidate_name}</span>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            {/* Кнопка "Готово" */}
            {session.candidate_ready_at ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                background: '#d4edda',
                color: '#155724',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '500',
                border: '1px solid #c3e6cb'
              }}>
                <CheckCircle size={18} />
                <span>Готовность отмечена</span>
              </div>
            ) : (
              <button
                onClick={markReady}
                disabled={isMarkingReady}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  background: isMarkingReady ? '#ccc' : '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: isMarkingReady ? 'not-allowed' : 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => {
                  if (!isMarkingReady) e.currentTarget.style.background = '#218838'
                }}
                onMouseLeave={(e) => {
                  if (!isMarkingReady) e.currentTarget.style.background = '#28a745'
                }}
              >
                <CheckCircle size={18} />
                {isMarkingReady ? 'Отправка...' : 'Завершить review'}
              </button>
            )}

            {/* ТАЙМЕР + ПРОГРЕСС-БАР */}
            <div 
              id="timer-container"
              style={{
                width: '320px',
                fontSize: '13px',
                fontFamily: 'monospace',
                background: 'rgba(0,0,0,0.05)',
                padding: '8px 12px',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease',
                animation: isBlinking ? 'blink 1s infinite' : 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontWeight: 'bold' }}>
                <Clock size={16} style={{ color: '#666' }} />
                <span style={{ flex: 1 }}>Осталось времени сессии</span>
                <span id="candidate-timer" style={{ color: '#2c3e50', fontFamily: 'monospace' }}>2:00:00</span>
              </div>
              <div style={{
                width: '100%',
                height: '10px',
                background: '#ddd',
                borderRadius: '5px',
                overflow: 'hidden',
                border: '1px solid #ccc'
              }}>
                <div
                  id="candidate-progress"
                  style={{
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, #27ae60 0%, #f39c12 60%, #e74c3c 100%)',
                    transition: 'all 0.8s ease',
                    boxShadow: '0 0 10px rgba(39,174,96,0.5)'
                  }}
                />
              </div>
            </div>
          </div>
        </header>

        {/* ОСНОВНОЙ КОНТЕНТ */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '40px',
          gap: '30px'
        }}>
          <div style={{
            textAlign: 'center',
            maxWidth: '600px'
          }}>
            <GitBranch size={64} style={{ color: '#3498db', marginBottom: '24px' }} />
            <h2 style={{ 
              fontSize: '28px', 
              fontWeight: '600', 
              marginBottom: '16px',
              color: '#2c3e50'
            }}>
              Pull Request открыт
            </h2>
            <p style={{ 
              fontSize: '16px', 
              color: '#666', 
              lineHeight: '1.6',
              marginBottom: '32px'
            }}>
              Ваш Pull Request автоматически открыт в новой вкладке. Таймер с оставшимся временем сессии открыт в отдельном окне.
              <br /><br />
              <strong>Работайте в Gitea, а таймер будет виден в отдельном окне.</strong>
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
              <a
                href={session.gitea.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 24px',
                  background: '#3498db',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: '500',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 2px 8px rgba(52, 152, 219, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#2980b9'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#3498db'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <GitBranch size={20} />
                <span>Открыть Gitea снова</span>
                <ExternalLink size={18} />
              </a>
              
              <button
                onClick={() => {
                  const timerUrl = `/timer/${token}`
                  const timerWindow = window.open(
                    timerUrl,
                    'timer-widget',
                    'width=400,height=320,resizable=yes,scrollbars=no,status=no,toolbar=no,menubar=no,location=no'
                  )
                  if (timerWindow) {
                    timerWindow.focus()
                    sessionStorage.setItem(`timer-opened-${token}`, 'true')
                  }
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '12px 24px',
                  background: '#27ae60',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 2px 8px rgba(39, 174, 96, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#229954'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#27ae60'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <Clock size={20} />
                <span>Открыть таймер снова</span>
              </button>
            </div>
          </div>
          
          <div style={{
            marginTop: '20px',
            padding: '16px 24px',
            background: '#e8f5e9',
            border: '1px solid #4caf50',
            borderRadius: '8px',
            fontSize: '14px',
            color: '#2e7d32',
            maxWidth: '500px',
            textAlign: 'center'
          }}>
            <strong>✅ Готово!</strong> Gitea и таймер открыты автоматически. 
            Если окна закрылись, используйте кнопки выше для повторного открытия.
          </div>
        </div>
      </div>
    )
  }

  // Если Gitea включена, но PR ещё не создан - показываем информационную страницу
  if (session.gitea?.enabled && !session.gitea?.pr_url) {
    return (
      <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '20px' }}>
        <div style={{ textAlign: 'center', maxWidth: '600px', padding: '40px' }}>
          <GitBranch size={48} style={{ color: '#3498db', marginBottom: '20px' }} />
          <h2 style={{ marginBottom: '16px' }}>Code Review Session</h2>
          <p style={{ color: '#666', marginBottom: '24px', lineHeight: '1.6' }}>
            Ваша сессия настроена для работы через Gitea. Репозиторий уже создан и готов к работе.
            {session.gitea.web_url ? (
              <>
                <br /><br />
                Нажмите кнопку ниже, чтобы открыть репозиторий и начать работу с кодом.
              </>
            ) : (
              <>
                <br /><br />
                Ожидайте, пока проверяющий создаст Pull Request для вашей сессии.
              </>
            )}
          </p>
          
          {session.gitea.web_url && (
            <a
              href={session.gitea.web_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 24px',
                background: '#3498db',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: '500',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#2980b9'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#3498db'}
            >
              <GitBranch size={18} />
              <span>Открыть репозиторий в Gitea</span>
              <ExternalLink size={16} />
            </a>
          )}
          
          <div style={{ marginTop: '32px', padding: '16px', background: '#f8f9fa', borderRadius: '8px', fontSize: '14px', color: '#666' }}>
            <strong>Информация о сессии:</strong>
            <br />
            Кандидат: {session.candidate_name}
            <br />
            Репозиторий: {session.gitea.user}/{session.gitea.repo}
          </div>
        </div>
      </div>
    )
  }

  // Обычный интерфейс (если Gitea не включена)
  return (
    <div className="container">
      <header>
        <div className="left">
          <span>Code Review Session</span>
          <span style={{ fontSize: '14px', color: '#666' }}> • {session.candidate_name}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          
          {/* Кнопка "Готово" */}
          {session.candidate_ready_at ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              background: '#d4edda',
              color: '#155724',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '500',
              border: '1px solid #c3e6cb'
            }}>
              <CheckCircle size={18} />
              <span>Готовность отмечена</span>
            </div>
          ) : (
            <button
              onClick={markReady}
              disabled={isMarkingReady}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                background: isMarkingReady ? '#ccc' : '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: isMarkingReady ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => {
                if (!isMarkingReady) e.currentTarget.style.background = '#218838'
              }}
              onMouseLeave={(e) => {
                if (!isMarkingReady) e.currentTarget.style.background = '#28a745'
              }}
            >
              <CheckCircle size={18} />
              {isMarkingReady ? 'Отправка...' : 'Завершить review'}
            </button>
          )}

          {/* ТАЙМЕР + ПРОГРЕСС-БАР (как в Reviewer Dashboard) */}
          <div 
            id="timer-container"
            style={{
              width: '320px',
              fontSize: '13px',
              fontFamily: 'monospace',
              background: 'rgba(0,0,0,0.05)',
              padding: '8px 12px',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              transition: 'all 0.3s ease',
              animation: isBlinking ? 'blink 1s infinite' : 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontWeight: 'bold' }}>
              <Clock size={16} style={{ color: '#666' }} />
              <span style={{ flex: 1 }}>Осталось времени сессии</span>
              <span id="candidate-timer" style={{ color: '#2c3e50', fontFamily: 'monospace' }}>2:00:00</span>
            </div>
            <div style={{
              width: '100%',
              height: '10px',
              background: '#ddd',
              borderRadius: '5px',
              overflow: 'hidden',
              border: '1px solid #ccc'
            }}>
              <div
                id="candidate-progress"
                style={{
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, #27ae60 0%, #f39c12 60%, #e74c3c 100%)',
                  transition: 'all 0.8s ease',
                  boxShadow: '0 0 10px rgba(39,174,96,0.5)'
                }}
              />
            </div>
          </div>
        </div>
      </header>

      <div className="main">
        <div className="editor-container">
          <Editor
            height="100%"
            defaultLanguage="diff"
            value={diffContent}
            theme="light"
            onMount={handleEditorDidMount}
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              lineNumbers: 'on',
              renderWhitespace: 'selection',
              folding: true,
              glyphMargin: true,
              readOnly: false
            }}
          />
        </div>

        <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-header">
            <MessageSquare size={18} /> Комментарии ({comments.length})
          </div>

          <div className="comment-list">
            {comments.length === 0 && !selectedLine ? (
              <div className="empty-state">
                {session.candidate_ready_at 
                  ? 'Готовность отмечена. Комментарии отправлены ревьюеру.'
                  : 'Кликните по строке, чтобы добавить комментарий'}
              </div>
            ) : (
              comments.map((c, i) => (
                <div key={i} className="comment-item" onClick={() => jumpToLine(c.line_range)}>
                  <div className="comment-file">{c.file}:{c.line_range}</div>
                  <div className="comment-type">
                    {c.type}
                    <span className={`severity-dot severity-${c.severity}`}></span>
                  </div>
                  <div className="comment-text">{c.text}</div>
                </div>
              ))
            )}
          </div>

          {selectedLine && !session.candidate_ready_at && (
            <div className="p-4 border-t border-gray-200 bg-gray-50">
              <h4 className="text-sm font-medium mb-3">
                Комментарий к строке {selectedLine}
              </h4>

              <select
                className="w-full p-2 text-sm border rounded mb-2"
                value={newComment.type}
                onChange={e => setNewComment({ ...newComment, type: e.target.value })}
              >
                <option value="bug">Bug</option>
                <option value="security">Security</option>
                <option value="style">Style</option>
                <option value="performance">Performance</option>
              </select>

              <select
                className="w-full p-2 text-sm border rounded mb-2"
                value={newComment.severity}
                onChange={e => setNewComment({ ...newComment, severity: e.target.value })}
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <textarea
                className="w-full p-2 text-sm border rounded mb-2 resize-none"
                rows={3}
                placeholder="Текст комментария..."
                value={newComment.text}
                onChange={e => setNewComment({ ...newComment, text: e.target.value })}
              />

              <div className="flex gap-2">
                <button
                  className="flex-1 btn btn-primary text-sm"
                  onClick={addComment}
                >
                  Добавить
                </button>
                <button
                  className="px-3 btn btn-secondary text-sm"
                  onClick={() => setSelectedLine(null)}
                >
                  Отмена
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {status && <div className="status-toast">{status}</div>}
    </div>
  )
}

