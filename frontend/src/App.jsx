// frontend/src/App.jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import Editor from '@monaco-editor/react'
import {
  Upload, Moon, Sun, FileText, MessageSquare,
  Plus, X, Menu, Loader2, LogOut, Clock, Timer
} from 'lucide-react'
import axios from 'axios'

const API_URL = '/api'

export default function App() {
  // ──────────────────────────────────────────────────────────────
  // Состояния
  // ──────────────────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') ?? 'light')
  const [sessionId, setSessionId] = useState(null)
  const [candidateId, setCandidateId] = useState('')
  const [diffContent, setDiffContent] = useState('')
  const [comments, setComments] = useState([])
  const [report, setReport] = useState('')
  const [status, setStatus] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [showReport, setShowReport] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [dragOver, setDragOver] = useState(false)

  const [selectedLine, setSelectedLine] = useState(null)
  const [newComment, setNewComment] = useState({
    file: 'main.py',
    line_range: '',
    type: 'bug',
    severity: 'medium',
    text: ''
  })

  // Состояния для таймера
  const [sessionCreatedAt, setSessionCreatedAt] = useState(null)
  const [showCreatedTimeModal, setShowCreatedTimeModal] = useState(false)
  const [isBlinking, setIsBlinking] = useState(false)
  const [notificationShown, setNotificationShown] = useState(false)

  const editorRef = useRef(null)
  const fileInputRef = useRef(null)
  const audioContextRef = useRef(null)
  const tickIntervalRef = useRef(null)
  const exitTimeoutRef = useRef(null)

  // ──────────────────────────────────────────────────────────────
  // Тема
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    document.body.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => (t === 'light' ? 'dark' : 'light'))

  // ──────────────────────────────────────────────────────────────
  // Загрузка сессии
  // ──────────────────────────────────────────────────────────────
  const loadSession = useCallback(async (id) => {
    setIsLoading(true)
    try {
      const [diffRes, sessRes] = await Promise.all([
        axios.get(`${API_URL}/artifacts/${id}_diff.patch`, { responseType: 'text' })
          .catch(() => ({ data: '# No diff available' })),
        axios.get(`${API_URL}/sessions/${id}`)
      ])
      setDiffContent(diffRes.data)
      setComments(sessRes.data.comments ?? [])
      
      // Сохраняем created_at и expires_at
      if (sessRes.data.created_at) {
        setSessionCreatedAt(sessRes.data.created_at)
      }
      if (sessRes.data.expires_at) {
        localStorage.setItem(`session_${id}`, JSON.stringify({
          expires_at: sessRes.data.expires_at,
          created_at: sessRes.data.created_at
        }))
      }

      try {
        const r = await axios.get(`${API_URL}/artifacts/${id}_report.txt`, { responseType: 'text' })
        setReport(r.data)
      } catch {}
    } catch (err) {
      setStatus('Ошибка загрузки сессии')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // ──────────────────────────────────────────────────────────────
  // Создание сессии
  // ──────────────────────────────────────────────────────────────
  const createSession = async () => {
    setIsLoading(true)
    try {
      const r = await axios.post(`${API_URL}/sessions`, {
        candidate_id: candidateId || 'anonymous',
        mr_package: 'demo_package'
      })
      setSessionId(r.data.session_id)
      setStatus(`Сессия #${r.data.session_id}`)
      await loadSession(r.data.session_id)
    } catch {
      setStatus('Ошибка создания')
    } finally {
      setIsLoading(false)
    }
  }

  // ──────────────────────────────────────────────────────────────
  // Выход
  // ──────────────────────────────────────────────────────────────
  const handleExit = useCallback(() => {
    setSessionId(null)
    setCandidateId('')
    setComments([])
    setDiffContent('')
    setReport('')
    setStatus('Вы вышли из сессии')
    setNotificationShown(false)
    if (tickIntervalRef.current) {
      clearInterval(tickIntervalRef.current)
      tickIntervalRef.current = null
    }
    if (exitTimeoutRef.current) {
      clearTimeout(exitTimeoutRef.current)
      exitTimeoutRef.current = null
    }
  }, [])

  // ──────────────────────────────────────────────────────────────
  // Drag & Drop .zip
  // ──────────────────────────────────────────────────────────────
  const uploadMR = async (file) => {
    if (!file?.name.endsWith('.zip')) {
      setStatus('Только .zip')
      return
    }
    const form = new FormData()
    form.append('file', file)
    setIsLoading(true)
    try {
      const r = await axios.post(`${API_URL}/upload-mr`, form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setSessionId(r.data.session_id)
      setStatus(`MR загружен: #${r.data.session_id}`)
      await loadSession(r.data.session_id)
    } catch (err) {
      setStatus('Ошибка загрузки MR')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // ──────────────────────────────────────────────────────────────
  // Оценка
  // ──────────────────────────────────────────────────────────────
  const evaluate = useCallback(async () => {
    if (!sessionId) return
    setIsEvaluating(true)
    try {
      const r = await axios.get(`${API_URL}/sessions/${sessionId}/evaluate`)
      setStatus(`Оценка: ${r.data.job_id}`)
      pollJob(r.data.job_id)
    } catch {
      setStatus('Ошибка запуска')
      setIsEvaluating(false)
    }
  }, [sessionId])

  const pollJob = (jobId) => {
    const iv = setInterval(async () => {
      try {
        const r = await axios.get(`${API_URL}/jobs/${jobId}`)
        if (r.data.status === 'finished') {
          clearInterval(iv)
          setIsEvaluating(false)
          const rep = await axios.get(`${API_URL}/artifacts/${sessionId}_report.txt`, { responseType: 'text' })
          setReport(rep.data)
          setStatus('Оценка завершена')
        }
      } catch {}
    }, 2000)
  }

  // ──────────────────────────────────────────────────────────────
  // Декорации в редакторе
  // ──────────────────────────────────────────────────────────────
  const updateDecorations = useCallback(() => {
    if (!editorRef.current || !comments.length) return
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

  useEffect(() => { updateDecorations() }, [updateDecorations])

  // ──────────────────────────────────────────────────────────────
  // Клик по строке → форма
  // ──────────────────────────────────────────────────────────────
  const handleEditorDidMount = (editor) => {
    editorRef.current = editor
    editor.onMouseDown(e => {
      if (e.target.type === 2) {
        const line = e.target.position.lineNumber
        setSelectedLine(line)
        setNewComment(p => ({ ...p, line_range: `${line}-${line}` }))
        setSidebarOpen(true)
      }
    })
    updateDecorations()
  }

  // ──────────────────────────────────────────────────────────────
  // Переход к строке
  // ──────────────────────────────────────────────────────────────
  const jumpToLine = (range) => {
    const [s] = range.split('-').map(Number)
    editorRef.current?.revealLineInCenter(s)
    editorRef.current?.setPosition({ lineNumber: s, column: 1 })
  }

  // ──────────────────────────────────────────────────────────────
  // Ctrl+Enter
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const h = e => { if (e.ctrlKey && e.key === 'Enter' && sessionId) evaluate() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [sessionId, evaluate])

  // ──────────────────────────────────────────────────────────────
  // Статус
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!status) return
    const t = setTimeout(() => setStatus(''), 3000)
    return () => clearTimeout(t)
  }, [status])

  // ──────────────────────────────────────────────────────────────
  // Функция для звука "тик-так"
  // ──────────────────────────────────────────────────────────────
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
      // Игнорируем ошибки звука (может быть заблокирован браузером)
    }
  }, [])

  // ──────────────────────────────────────────────────────────────
  // Функция для уведомления браузера
  // ──────────────────────────────────────────────────────────────
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

  // ──────────────────────────────────────────────────────────────
  // Функция для продления сессии
  // ──────────────────────────────────────────────────────────────
  const extendSession = useCallback(async () => {
    if (!sessionId) return
    try {
      const r = await axios.post(`${API_URL}/sessions/${sessionId}/extend`)
      
      // Проверяем, что получили корректное expires_at
      if (!r.data.expires_at) {
        console.error('Ошибка: не получен expires_at от сервера')
        setStatus('Ошибка: не получено новое время')
        return
      }
      
      console.log('Продление сессии:', {
        old: JSON.parse(localStorage.getItem(`session_${sessionId}`) || '{}').expires_at,
        new: r.data.expires_at
      })
      
      setStatus('Сессия продлена на 30 минут')
      
      // Обновляем localStorage с новым expires_at
      const lastSessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || '{}')
      localStorage.setItem(`session_${sessionId}`, JSON.stringify({
        ...lastSessionData,
        expires_at: r.data.expires_at
      }))
      
      // Сбрасываем флаг уведомления, чтобы можно было показать снова при необходимости
      setNotificationShown(false)
      
      // Отменяем таймаут выхода, если он был установлен (время было продлено)
      if (exitTimeoutRef.current) {
        clearTimeout(exitTimeoutRef.current)
        exitTimeoutRef.current = null
      }
      
      // Принудительно обновляем таймер, чтобы он сразу увидел новое время
      // Это предотвратит вызов handleExit() если таймер уже проверил старое время
      const timerEl = document.getElementById('session-timer')
      const progressEl = document.getElementById('session-progress')
      if (timerEl && progressEl) {
        // Триггерим обновление таймера немедленно
        const updateTimer = () => {
          const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || '{}')
          const expiresAt = sessionData.expires_at || r.data.expires_at
          
          if (!expiresAt) return
          
          const now = Date.now()
          const expiresAtUTC = expiresAt.endsWith('Z') || expiresAt.includes('+') || expiresAt.includes('-') 
            ? expiresAt 
            : expiresAt + 'Z'
          const end = new Date(expiresAtUTC).getTime()
          const diff = Math.max(0, end - now)
          
          if (diff === 0) {
            timerEl.textContent = 'Время вышло!'
            progressEl.style.width = '0%'
            progressEl.style.background = '#e74c3c'
            return
          }
          
          const hours = Math.floor(diff / (1000 * 60 * 60))
          const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
          const seconds = Math.floor((diff % (1000 * 60)) / 1000)
          
          timerEl.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
          
          const total = 2 * 60 * 60 * 1000
          const percent = (diff / total) * 100
          progressEl.style.width = `${percent}%`
          
          if (percent < 15) {
            progressEl.style.background = '#e74c3c'
          } else if (percent < 40) {
            progressEl.style.background = '#f39c12'
          } else {
            progressEl.style.background = '#27ae60'
          }
        }
        updateTimer()
      }
    } catch (err) {
      setStatus('Ошибка продления сессии')
      console.error(err)
    }
  }, [sessionId])

  // ──────────────────────────────────────────────────────────────
  // ТАЙМЕР СЕССИИ + ПРОГРЕСС-БАР (УЛУЧШЕННАЯ ВЕРСИЯ)
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) {
      // Очищаем интервалы при выходе
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current)
        tickIntervalRef.current = null
      }
      return
    }

    const updateTimer = () => {
      const timerEl = document.getElementById('session-timer')
      const progressEl = document.getElementById('session-progress')
      const timerContainer = document.getElementById('timer-container')
      if (!timerEl || !progressEl) return

      // Получаем expires_at из последней загруженной сессии
      const lastSessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || '{}')
      const expiresAt = lastSessionData.expires_at

      if (!expiresAt) {
        timerEl.textContent = '—:—:—'
        return
      }

      const now = Date.now()
      // Парсим expiresAt как UTC (если есть Z в конце, JavaScript автоматически распознает UTC)
      // Если Z нет, добавляем его для явного указания UTC
      const expiresAtUTC = expiresAt.endsWith('Z') || expiresAt.includes('+') || expiresAt.includes('-') 
        ? expiresAt 
        : expiresAt + 'Z'
      const end = new Date(expiresAtUTC).getTime()
      const diff = Math.max(0, end - now)

      if (diff === 0) {
        timerEl.textContent = 'Время вышло!'
        progressEl.style.width = '0%'
        progressEl.style.background = '#e74c3c'
        // Очищаем предыдущий таймаут выхода, если он был установлен
        if (exitTimeoutRef.current) {
          clearTimeout(exitTimeoutRef.current)
        }
        // Добавляем небольшую задержку перед выходом, чтобы дать время для обновления после продления
        // Это предотвращает случайный выход сразу после продления сессии
        exitTimeoutRef.current = setTimeout(() => {
          // Проверяем еще раз перед выходом - возможно, время было продлено
          const recheckData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || '{}')
          const recheckExpires = recheckData.expires_at
          if (recheckExpires) {
            const recheckExpiresUTC = recheckExpires.endsWith('Z') || recheckExpires.includes('+') || recheckExpires.includes('-') 
              ? recheckExpires 
              : recheckExpires + 'Z'
            const recheckEnd = new Date(recheckExpiresUTC).getTime()
            const recheckDiff = Math.max(0, recheckEnd - Date.now())
            // Если время все еще истекло после повторной проверки, только тогда выходим
            if (recheckDiff === 0) {
              handleExit()
            }
            // Если время было продлено, таймер обновится автоматически на следующей итерации
          } else {
        handleExit()
          }
          exitTimeoutRef.current = null
        }, 1000) // Задержка 1 секунда для проверки обновления
        return
      } else {
        // Если время не истекло, отменяем таймаут выхода (если он был установлен)
        if (exitTimeoutRef.current) {
          clearTimeout(exitTimeoutRef.current)
          exitTimeoutRef.current = null
        }
      }

      const hours = Math.floor(diff / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)
      const totalMinutes = hours * 60 + minutes

      timerEl.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`

      const total = 2 * 60 * 60 * 1000 // 2 часа
      const percent = (diff / total) * 100
      progressEl.style.width = `${percent}%`

      // Цвет по оставшемуся времени
      if (percent < 15) {
        progressEl.style.background = '#e74c3c'
      } else if (percent < 40) {
        progressEl.style.background = '#f39c12'
      } else {
        progressEl.style.background = '#27ae60'
      }

      // Мигание при < 5 минут
      if (totalMinutes < 5) {
        setIsBlinking(true)
        if (timerContainer) {
          timerContainer.style.animation = 'blink 1s infinite'
        }
      } else {
        setIsBlinking(false)
        if (timerContainer) {
          timerContainer.style.animation = 'none'
        }
      }

      // Звук "тик-так" при < 1 минуте
      if (totalMinutes < 1) {
        if (!tickIntervalRef.current) {
          playTickSound() // Первый тик сразу
          tickIntervalRef.current = setInterval(() => {
            playTickSound()
          }, 1000)
        }
      } else {
        if (tickIntervalRef.current) {
          clearInterval(tickIntervalRef.current)
          tickIntervalRef.current = null
        }
      }

      // Уведомление браузера при < 10 минут (один раз)
      if (totalMinutes < 10 && !notificationShown) {
        showBrowserNotification(`Внимание! Осталось менее 10 минут до окончания сессии.`)
        setNotificationShown(true)
      }
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => {
      clearInterval(interval)
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current)
        tickIntervalRef.current = null
      }
    }
  }, [sessionId, playTickSound, showBrowserNotification, notificationShown, handleExit])

  // Сохраняем expires_at при загрузке сессии
  useEffect(() => {
    if (sessionId) {
      axios.get(`${API_URL}/sessions/${sessionId}`).then(res => {
        localStorage.setItem(`session_${sessionId}`, JSON.stringify({
          expires_at: res.data.expires_at,
          created_at: res.data.created_at
        }))
        if (res.data.created_at) {
          setSessionCreatedAt(res.data.created_at)
        }
        setNotificationShown(false) // Сбрасываем при загрузке новой сессии
      })
    }
  }, [sessionId])

  // ──────────────────────────────────────────────────────────────
  // Стартовый экран
  // ──────────────────────────────────────────────────────────────
  if (!sessionId) {
    return (
      <div className="start-screen">
        <div className="start-card">
          <h1>Code Review Platform</h1>

          <div className="input-group">
            <input
              placeholder="ID кандидата (необязательно)"
              value={candidateId}
              onChange={e => setCandidateId(e.target.value)}
            />
          </div>

          <button className="btn btn-primary" onClick={createSession} disabled={isLoading}>
            {isLoading ? <Loader2 size={16} /> : <Plus size={16} />}
            Создать сессию
          </button>

          <div className="or-divider"><span>или</span></div>

          <div
            className={`dropzone ${dragOver ? 'dragover' : ''}`}
            onDrop={e => { e.preventDefault(); setDragOver(false); uploadMR(e.dataTransfer.files[0]) }}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={32} />
            <p>Перетащите .zip с MR</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={e => uploadMR(e.target.files[0])}
              style={{ display: 'none' }}
            />
          </div>
        </div>
      </div>
    )
  }

  // ──────────────────────────────────────────────────────────────
  // Основной интерфейс
  // ──────────────────────────────────────────────────────────────
  return (
    <div className="container">
      {/* HEADER */}
     <header>
  <div className="left">
    <button className="btn-icon mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
      <Menu size={20} />
    </button>
    <span>Session <span className="session-id">#{sessionId}</span></span>
    <span style={{ fontSize: '14px', color: '#666' }}> • {candidateId || 'anonymous'}</span>
  </div>

  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
    {/* ТАЙМЕР + ПРОГРЕСС-БАР (УЛУЧШЕННАЯ ВЕРСИЯ) */}
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
        cursor: 'pointer',
        transition: 'all 0.3s ease'
      }}
      onClick={() => {
        if (sessionCreatedAt) {
          const createdDate = new Date(sessionCreatedAt)
          const formatted = createdDate.toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })
          setStatus(`Сессия создана: ${formatted}`)
        } else {
          setStatus('Время создания недоступно')
        }
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(0,0,0,0.08)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(0,0,0,0.05)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontWeight: 'bold' }}>
        <Clock size={16} style={{ color: '#666' }} />
        <span style={{ flex: 1 }}>Осталось времени сессии</span>
        <span id="session-timer" style={{ color: '#2c3e50', fontFamily: 'monospace' }}>2:00:00</span>
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
          id="session-progress"
          style={{
            width: '100%',
            height: '100%',
            background: 'linear-gradient(90deg, #27ae60 0%, #f39c12 60%, #e74c3c 100%)',
            transition: 'all 0.8s ease',
            boxShadow: '0 0 10px rgba(39,174,96,0.5)'
          }}
        />
      </div>
      {/* Кнопка продления сессии */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          extendSession()
        }}
        style={{
          marginTop: '6px',
          width: '100%',
          padding: '4px 8px',
          fontSize: '11px',
          background: '#3498db',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '4px',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#2980b9'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = '#3498db'
        }}
      >
        <Timer size={12} />
        Продлить на 30 мин
      </button>
    </div>

    {/* КНОПКИ */}
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
      <button className="btn btn-secondary" onClick={() => setShowReport(true)}>
        Отчёт
      </button>

      <a
        href={`/api/sessions/${sessionId}/report/pdf`}
        target="_blank"
        rel="noopener noreferrer"
        className="btn"
        style={{ background: '#27ae60', color: 'white', display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0  talvez 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
        PDF
      </a>

      <button className="btn btn-primary" onClick={evaluate} disabled={isEvaluating}>
        {isEvaluating ? <Loader2 size={16} className="animate-spin" /> : null}
        Оценить
      </button>

      <button className="btn" onClick={handleExit} style={{ background: '#dc3545', color: 'white' }}>
        <LogOut size={16} /> Выйти
      </button>

      <button className="btn-icon" onClick={toggleTheme}>
        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
      </button>
    </div>
  </div>
</header>

      {/* MAIN */}
      <div className="main">
        <div className="editor-container">
          {isLoading ? (
            <div style={{ padding: '20px' }}>
              {[...Array(20)].map((_, i) => (
                <div key={i} className="skeleton loading-line"
                     style={{ width: `${70 + i % 30}%` }}></div>
              ))}
            </div>
          ) : (
            <Editor
              height="100%"
              defaultLanguage="diff"
              value={diffContent}
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
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
              }}
            />
          )}
        </div>

        <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-header">
            <MessageSquare size={18} /> Комментарии ({comments.length})
          </div>

          <div className="comment-list">
            {comments.length === 0 && !selectedLine ? (
              <div className="empty-state">
                Кликните по строке, чтобы добавить комментарий
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

          {selectedLine && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
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
                  onClick={async () => {
                    try {
                      await axios.post(`${API_URL}/sessions/${sessionId}/comments`, newComment)
                      setSelectedLine(null)
                      setNewComment({ ...newComment, text: '', line_range: '' })
                      await loadSession(sessionId)
                      setStatus('Комментарий добавлен')
                    } catch (err) {
                      console.error(err)
                      setStatus('Ошибка добавления')
                    }
                  }}
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

      {showReport && (
        <div className="modal" onClick={() => setShowReport(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span>Отчёт по сессии #{sessionId}</span>
              <button className="btn-icon" onClick={() => setShowReport(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              {report || 'Отчёт ещё не готов...'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}