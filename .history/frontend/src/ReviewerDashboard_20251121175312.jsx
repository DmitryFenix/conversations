// frontend/src/ReviewerDashboard.jsx
import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Plus, Moon, Sun, FileText, MessageSquare, Timer, LogOut, ArrowLeft, Copy, ExternalLink, GitBranch, RefreshCw, GitMerge, Trash2, CheckCircle, X, Clock } from 'lucide-react'
import axios from 'axios'

const API_URL = '/api'

export default function ReviewerDashboard() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') ?? 'light')
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [giteaPR, setGiteaPR] = useState(null)
  const [isLoadingPR, setIsLoadingPR] = useState(false)
  const [newSession, setNewSession] = useState({
    candidate_name: '',
    mr_package: 'demo_package',
    reviewer_name: 'Reviewer'
  })
  const [createdSessionInfo, setCreatedSessionInfo] = useState(null) // Информация о созданной сессии для модального окна
  const [linkCopied, setLinkCopied] = useState(false) // Флаг, что ссылка скопирована
  const tickIntervalRef = useRef(null) // Для таймера

  // Загрузка списка сессий
  useEffect(() => {
    loadSessions()
    if (sessionId) {
      loadSession(parseInt(sessionId))
    }
  }, [sessionId])

  // Таймер сессии с прогресс-баром (для детального вида)
  useEffect(() => {
    if (!sessionId || !selectedSession) {
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current)
        tickIntervalRef.current = null
      }
      return
    }

    const updateTimer = () => {
      const timerEl = document.getElementById('reviewer-session-timer')
      const progressEl = document.getElementById('reviewer-session-progress')
      if (!timerEl || !progressEl) return

      const expiresAt = selectedSession.expires_at
      if (!expiresAt) {
        timerEl.textContent = '—:—:—'
        return
      }

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
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    tickIntervalRef.current = interval

    return () => {
      clearInterval(interval)
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current)
        tickIntervalRef.current = null
      }
    }
  }, [sessionId, selectedSession])

  const loadSessions = async () => {
    try {
      const res = await axios.get(`${API_URL}/reviewer/sessions`)
      setSessions(res.data.sessions || [])
    } catch (err) {
      console.error('Ошибка загрузки сессий:', err)
    }
  }

  const loadSession = async (id) => {
    setIsLoading(true)
    try {
      const res = await axios.get(`${API_URL}/reviewer/sessions/${id}`)
      setSelectedSession(res.data)
      
      // Сохраняем expires_at в localStorage для таймера
      if (res.data.expires_at) {
        localStorage.setItem(`session_${id}`, JSON.stringify({
          expires_at: res.data.expires_at,
          created_at: res.data.created_at
        }))
      }
      
      // Если есть Gitea PR, загружаем его
      if (res.data.gitea?.pr_id) {
        loadGiteaPR(id)
      }
    } catch (err) {
      console.error('Ошибка загрузки сессии:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadGiteaPR = async (sessionId) => {
    setIsLoadingPR(true)
    try {
      const res = await axios.get(`${API_URL}/reviewer/sessions/${sessionId}/gitea/pr`)
      setGiteaPR(res.data)
    } catch (err) {
      // PR может быть не создан, это нормально
      if (err.response?.status !== 404) {
        console.error('Ошибка загрузки PR:', err)
      }
      setGiteaPR(null)
    } finally {
      setIsLoadingPR(false)
    }
  }

  const createGiteaPR = async (sessionId) => {
    setIsLoadingPR(true)
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions/${sessionId}/gitea/create-pr`)
      await loadSession(sessionId)
      await loadGiteaPR(sessionId)
    } catch (err) {
      console.error('Ошибка создания PR:', err)
    } finally {
      setIsLoadingPR(false)
    }
  }

  const syncGiteaComments = async (sessionId) => {
    setIsLoadingPR(true)
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions/${sessionId}/gitea/sync-comments`)
      if (res.data.errors && res.data.errors.length > 0) {
        console.warn('Ошибки синхронизации:', res.data.errors)
      }
      await loadGiteaPR(sessionId)
      if (selectedSession && selectedSession.id === sessionId) {
        loadSession(sessionId)
      }
    } catch (err) {
      console.error('Ошибка синхронизации:', err)
    } finally {
      setIsLoadingPR(false)
    }
  }

  const syncCommentsFromGitea = async (sessionId) => {
    setIsLoadingPR(true)
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions/${sessionId}/gitea/sync-comments-from-gitea`)
      await loadGiteaPR(sessionId)
      if (selectedSession && selectedSession.id === sessionId) {
        loadSession(sessionId)
      }
    } catch (err) {
      console.error('Ошибка синхронизации из Gitea:', err)
    } finally {
      setIsLoadingPR(false)
    }
  }

  const createSession = async () => {
    if (!newSession.candidate_name.trim()) {
      return
    }

    setIsLoading(true)
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions`, newSession)
      const createdSession = res.data
      
      // Сохраняем информацию о созданной сессии для показа в модальном окне
      const tokenUrl = `${window.location.origin}/candidate/${createdSession.access_token}`
      setLinkCopied(false) // Сбрасываем флаг копирования
      setCreatedSessionInfo({
        sessionId: createdSession.session_id,
        accessToken: createdSession.access_token,
        tokenUrl: tokenUrl
      })
      
      setNewSession({ candidate_name: '', mr_package: 'demo_package', reviewer_name: 'Reviewer' })
      setShowCreateForm(false)
      loadSessions()
    } catch (err) {
      console.error('Ошибка создания сессии:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopyTokenUrl = async () => {
    if (createdSessionInfo) {
      try {
        await navigator.clipboard.writeText(createdSessionInfo.tokenUrl)
        setLinkCopied(true)
        // Автоматически закрываем через 2 секунды после копирования
        setTimeout(() => {
          const sessionId = createdSessionInfo.sessionId
          setCreatedSessionInfo(null)
          setLinkCopied(false)
          navigate(`/reviewer/sessions/${sessionId}`)
        }, 2000)
      } catch (err) {
        console.error('Ошибка копирования:', err)
        console.error('Не удалось скопировать ссылку')
      }
    }
  }

  const handleCloseSuccessModal = () => {
    const sessionId = createdSessionInfo?.sessionId
    setCreatedSessionInfo(null)
    setLinkCopied(false)
    if (sessionId) {
      navigate(`/reviewer/sessions/${sessionId}`)
    }
  }

  const extendSession = async (id) => {
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions/${id}/extend`)
      if (selectedSession && selectedSession.id === id) {
        const updatedSession = { ...selectedSession, expires_at: res.data.expires_at }
        setSelectedSession(updatedSession)
        // Сохраняем в localStorage для таймера
        localStorage.setItem(`session_${id}`, JSON.stringify({
          expires_at: res.data.expires_at,
          created_at: selectedSession.created_at
        }))
      }
      loadSessions()
    } catch (err) {
      console.error('Ошибка продления:', err)
    }
  }

  const evaluateSession = async (id) => {
    setIsLoading(true)
    try {
      const res = await axios.post(`${API_URL}/reviewer/sessions/${id}/evaluate`)
      // Можно добавить polling для проверки статуса
    } catch (err) {
      console.error('Ошибка оценки:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const deleteSession = async (id, candidateName) => {
    setIsLoading(true)
    try {
      await axios.delete(`${API_URL}/reviewer/sessions/${id}`)
      loadSessions()
      // Если удаляемая сессия была открыта, возвращаемся к списку
      if (selectedSession && selectedSession.id === id) {
        setSelectedSession(null)
        navigate('/reviewer')
      }
    } catch (err) {
      console.error('Ошибка удаления:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const finishSession = async (id) => {
    setIsLoading(true)
    try {
      await axios.post(`${API_URL}/reviewer/sessions/${id}/finish`)
      loadSessions()
      if (selectedSession && selectedSession.id === id) {
        loadSession(id)
      }
    } catch (err) {
      console.error('Ошибка завершения:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.body.classList.toggle('dark', newTheme === 'dark')
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    try {
      const date = new Date(dateStr)
      return date.toLocaleString('ru-RU')
    } catch {
      return dateStr
    }
  }

  // Если выбран sessionId, показываем детали сессии
  if (sessionId && selectedSession) {
    return (
      <div className="container">
        <header>
          <div className="left">
            <button className="btn-icon" onClick={() => navigate('/reviewer')}>
              <ArrowLeft size={18} />
            </button>
            <span>Сессия #{selectedSession.id}</span>
            <span style={{ fontSize: '14px', color: '#666' }}> • {selectedSession.candidate_name}</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            {selectedSession.candidate_ready_at && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                background: '#d4edda',
                color: '#155724',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                border: '1px solid #c3e6cb'
              }}>
                <CheckCircle size={16} />
                Кандидат готов
              </div>
            )}
            
            {/* ТАЙМЕР + ПРОГРЕСС-БАР */}
            <div 
              id="reviewer-timer-container"
              style={{
                width: '320px',
                fontSize: '13px',
                fontFamily: 'monospace',
                background: 'rgba(0,0,0,0.05)',
                padding: '8px 12px',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontWeight: 'bold' }}>
                <Clock size={16} style={{ color: '#666' }} />
                <span style={{ flex: 1 }}>Осталось времени сессии</span>
                <span id="reviewer-session-timer" style={{ color: '#2c3e50', fontFamily: 'monospace' }}>2:00:00</span>
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
                  id="reviewer-session-progress"
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
                  extendSession(selectedSession.id)
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
            
            <button 
              className="btn" 
              onClick={() => finishSession(selectedSession.id)}
              style={{ background: '#dc3545', color: 'white' }}
              disabled={isLoading}
            >
              Завершить сессию
            </button>
            <a
              href={`${API_URL}/reviewer/sessions/${selectedSession.id}/report/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ background: '#3498db', color: 'white' }}
            >
              <FileText size={16} />
              Отчёт (PDF)
            </a>
            <button className="btn btn-primary" onClick={() => evaluateSession(selectedSession.id)} disabled={isLoading}>
              Оценить
            </button>
            <a
              href={`/candidate/${selectedSession.access_token}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
            >
              <ExternalLink size={16} />
              Открыть как кандидат
            </a>
            <button 
              className="btn btn-secondary"
              onClick={() => deleteSession(selectedSession.id, selectedSession.candidate_name)}
              style={{ color: '#e74c3c' }}
            >
              <Trash2 size={16} />
              Удалить
            </button>
            <button className="btn-icon" onClick={toggleTheme}>
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </header>

        <div className="main" style={{ padding: '20px' }}>
          {selectedSession.deleted_at && (
            <div style={{
              padding: '12px 16px',
              background: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '8px',
              marginBottom: '20px',
              color: '#856404'
            }}>
              ⚠️ Эта сессия была удалена {formatDate(selectedSession.deleted_at)}
            </div>
          )}
          {/* Статистика по комментариям */}
          {selectedSession.comments && selectedSession.comments.length > 0 && (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: '16px', 
              marginBottom: '20px' 
            }}>
              {(() => {
                const comments = selectedSession.comments || []
                const bySeverity = comments.reduce((acc, c) => {
                  const sev = c.severity || 'medium'
                  acc[sev] = (acc[sev] || 0) + 1
                  return acc
                }, {})
                const byType = comments.reduce((acc, c) => {
                  const type = c.type || 'comment'
                  acc[type] = (acc[type] || 0) + 1
                  return acc
                }, {})
                
                return (
                  <>
                    <div style={{
                      background: 'white',
                      padding: '20px',
                      borderRadius: '12px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      border: '1px solid #e9ecef'
                    }}>
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Всего комментариев
                      </div>
                      <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#3498db' }}>
                        {comments.length}
                      </div>
                    </div>
                    {Object.entries(bySeverity).map(([severity, count]) => {
                      const colors = {
                        critical: { bg: '#ffebee', color: '#c62828', label: 'Критичные' },
                        high: { bg: '#fff3e0', color: '#e65100', label: 'Высокий' },
                        medium: { bg: '#fffde7', color: '#f57f17', label: 'Средний' },
                        low: { bg: '#f3f4f7', color: '#546e7a', label: 'Низкий' }
                      }
                      const style = colors[severity] || colors.medium
                      return (
                        <div key={severity} style={{
                          background: 'white',
                          padding: '20px',
                          borderRadius: '12px',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                          border: '1px solid #e9ecef'
                        }}>
                          <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            {style.label}
                          </div>
                          <div style={{ fontSize: '32px', fontWeight: 'bold', color: style.color }}>
                            {count}
                          </div>
                        </div>
                      )
                    })}
                  </>
                )
              })()}
            </div>
          )}

          <div className="card">
            <h2>Информация о сессии</h2>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
              gap: '20px', 
              marginTop: '20px' 
            }}>
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Кандидат
                </div>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#1a1a1a' }}>
                  {selectedSession.candidate_name}
                </div>
              </div>
              
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Проверяющий
                </div>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#1a1a1a' }}>
                  {selectedSession.reviewer_name || 'Не указан'}
                </div>
              </div>
              
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  MR Package
                </div>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#1a1a1a', fontFamily: 'monospace' }}>
                  {selectedSession.mr_package}
                </div>
              </div>
              
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Статус
                </div>
                <div>
                  <span style={{
                    display: 'inline-block',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '13px',
                    fontWeight: '600',
                    background: selectedSession.status === 'active' ? '#d4edda' : 
                               selectedSession.status === 'finished' ? '#cce5ff' : 
                               selectedSession.status === 'expired' ? '#f8d7da' : '#e2e3e5',
                    color: selectedSession.status === 'active' ? '#155724' : 
                          selectedSession.status === 'finished' ? '#004085' : 
                          selectedSession.status === 'expired' ? '#721c24' : '#383d41'
                  }}>
                    {selectedSession.status === 'active' ? 'Активна' : 
                     selectedSession.status === 'finished' ? 'Завершена' : 
                     selectedSession.status === 'expired' ? 'Истекла' : 
                     selectedSession.status || 'active'}
                  </span>
                </div>
              </div>
              
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Создано
                </div>
                <div style={{ fontSize: '14px', color: '#1a1a1a' }}>
                  {formatDate(selectedSession.created_at)}
                </div>
              </div>
              
              <div style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Истекает
                </div>
                <div style={{ fontSize: '14px', color: '#1a1a1a' }}>
                  {formatDate(selectedSession.expires_at)}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '20px', padding: '16px', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e9ecef' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Токен кандидата
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <code style={{ 
                  flex: 1,
                  fontSize: '12px', 
                  background: 'white', 
                  padding: '8px 12px', 
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontFamily: 'monospace',
                  wordBreak: 'break-all'
                }}>
                  {selectedSession.access_token}
                </code>
                <button
                  className="btn-icon"
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/candidate/${selectedSession.access_token}`)
                  }}
                  style={{
                    padding: '8px',
                    background: '#3498db',
                    color: 'white',
                    borderRadius: '6px',
                    border: 'none',
                    cursor: 'pointer'
                  }}
                  title="Копировать ссылку для кандидата"
                >
                  <Copy size={16} />
                </button>
              </div>
            </div>

            <div style={{ marginTop: '20px' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Готовность кандидата
              </div>
              {selectedSession.candidate_ready_at ? (
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 16px',
                  background: '#d4edda',
                  color: '#155724',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  border: '1px solid #c3e6cb'
                }}>
                  <CheckCircle size={18} />
                  Готов с {formatDate(selectedSession.candidate_ready_at)}
                </div>
              ) : (
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 16px',
                  background: '#fff3cd',
                  color: '#856404',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  border: '1px solid #ffc107'
                }}>
                  <Clock size={18} />
                  Ожидает...
                </div>
              )}
            </div>
          </div>

          {/* Gitea Integration Section */}
          {selectedSession.gitea?.enabled && (
            <div style={{ marginTop: '30px', padding: '20px', background: '#f0f7ff', borderRadius: '8px', border: '1px solid #3498db' }}>
              <h3 style={{ marginTop: 0, marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitBranch size={20} />
                Gitea Integration
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '10px', marginBottom: '15px' }}>
                <div><strong>Пользователь:</strong></div>
                <div>{selectedSession.gitea.user}</div>
                
                <div><strong>Репозиторий:</strong></div>
                <div>{selectedSession.gitea.repo}</div>
                
                {selectedSession.gitea.web_url && (
                  <>
                    <div><strong>Web URL:</strong></div>
                    <div>
                      <a href={selectedSession.gitea.web_url} target="_blank" rel="noopener noreferrer" style={{ color: '#3498db' }}>
                        {selectedSession.gitea.web_url}
                        <ExternalLink size={14} style={{ marginLeft: '4px', display: 'inline' }} />
                      </a>
                    </div>
                  </>
                )}
                
                {selectedSession.gitea.pr_id ? (
                  <>
                    <div><strong>Pull Request:</strong></div>
                    <div>
                      <a 
                        href={`${selectedSession.gitea.web_url}/pulls/${selectedSession.gitea.pr_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#3498db', marginRight: '10px' }}
                      >
                        PR #{selectedSession.gitea.pr_id}
                        <ExternalLink size={14} style={{ marginLeft: '4px', display: 'inline' }} />
                      </a>
                      {giteaPR && (
                        <span style={{ fontSize: '12px', color: '#666', marginLeft: '10px' }}>
                          {giteaPR.pr?.state || 'open'}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <div><strong>Pull Request:</strong></div>
                    <div>
                      <button
                        className="btn btn-secondary"
                        onClick={() => createGiteaPR(selectedSession.id)}
                        disabled={isLoadingPR}
                        style={{ fontSize: '12px', padding: '6px 12px' }}
                      >
                        <GitMerge size={14} />
                        Создать PR
                      </button>
                    </div>
                  </>
                )}
              </div>
              
              {selectedSession.gitea.pr_id && (
                <div style={{ display: 'flex', gap: '8px', marginTop: '15px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => loadGiteaPR(selectedSession.id)}
                    disabled={isLoadingPR}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    <RefreshCw size={14} />
                    Обновить PR
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => syncCommentsFromGitea(selectedSession.id)}
                    disabled={isLoadingPR}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                    title="Синхронизировать комментарии из Gitea PR в нашу систему (для отчёта)"
                  >
                    <RefreshCw size={14} />
                    Загрузить комментарии из Gitea
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => syncGiteaComments(selectedSession.id)}
                    disabled={isLoadingPR}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                    title="Отправить комментарии из нашей системы в Gitea PR"
                  >
                    <GitMerge size={14} />
                    Отправить в Gitea
                  </button>
                </div>
              )}
              
              {giteaPR && (
                <div style={{ marginTop: '15px', padding: '10px', background: 'white', borderRadius: '4px' }}>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
                    Комментариев в PR: {giteaPR.comments?.length || 0}
                  </div>
                  {giteaPR.pr?.body && (
                    <div style={{ fontSize: '12px', color: '#333', marginTop: '5px' }}>
                      <strong>Описание:</strong> {giteaPR.pr.body.substring(0, 100)}...
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="card" style={{ marginTop: '20px' }}>
            <h2 style={{ marginTop: 0 }}>Комментарии ({selectedSession.comments?.length || 0})</h2>
            {selectedSession.comments && selectedSession.comments.length > 0 ? (
              <div>
                {selectedSession.comments.map((comment, i) => {
                  const severityColors = {
                    critical: { border: '#c62828', bg: '#ffebee' },
                    high: { border: '#e65100', bg: '#fff3e0' },
                    medium: { border: '#f57f17', bg: '#fffde7' },
                    low: { border: '#546e7a', bg: '#f3f4f7' }
                  }
                  const style = severityColors[comment.severity] || severityColors.medium
                  
                  return (
                    <div key={i} style={{ 
                      padding: '16px', 
                      marginBottom: '12px', 
                      background: style.bg, 
                      borderRadius: '8px',
                      borderLeft: `4px solid ${style.border}`,
                      border: `1px solid ${style.border}20`,
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateX(4px)'
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateX(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                        <div>
                          <strong style={{ fontSize: '14px', color: '#1a1a1a' }}>
                            {comment.file}
                          </strong>
                          <span style={{ fontSize: '13px', color: '#666', marginLeft: '8px' }}>
                            строки {comment.line_range}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ 
                            fontSize: '11px', 
                            padding: '4px 8px',
                            background: 'white',
                            borderRadius: '12px',
                            color: '#666',
                            fontWeight: '500'
                          }}>
                            {comment.type}
                          </span>
                          <span style={{ 
                            fontSize: '11px', 
                            padding: '4px 8px',
                            background: style.border,
                            color: 'white',
                            borderRadius: '12px',
                            fontWeight: '600',
                            textTransform: 'uppercase'
                          }}>
                            {comment.severity}
                          </span>
                        </div>
                      </div>
                      <div style={{ 
                        fontSize: '14px', 
                        color: '#333',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {comment.text}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div style={{
                padding: '40px',
                textAlign: 'center',
                color: '#999',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '1px dashed #ddd'
              }}>
                <MessageSquare size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
                <p style={{ margin: 0, fontSize: '16px' }}>Комментариев пока нет</p>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Список сессий
  return (
    <div className="container">
      <header>
        <div className="left">
          <span>Code Review Platform - Reviewer</span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-primary" onClick={() => setShowCreateForm(true)}>
            <Plus size={16} />
            Создать сессию
          </button>
          <button className="btn-icon" onClick={toggleTheme}>
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>

      <div className="main" style={{ 
        padding: '20px', 
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        height: '100%'
      }}>
        {/* Модальное окно успешного создания сессии */}
        {createdSessionInfo && (
          <div 
            className="modal" 
            onClick={handleCloseSuccessModal}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1001,
              animation: 'fadeIn 0.2s ease-out'
            }}
          >
            <div 
              className="modal-content" 
              onClick={e => e.stopPropagation()}
              style={{
                background: theme === 'dark' ? '#2d2d2d' : 'white',
                borderRadius: '16px',
                width: '90%',
                maxWidth: '520px',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                animation: 'slideUp 0.3s ease-out',
                overflow: 'hidden'
              }}
            >
              <div style={{
                padding: '24px 28px',
                borderBottom: theme === 'dark' ? '1px solid #444' : '1px solid #e9ecef',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'linear-gradient(135deg, #27ae60 0%, #2ecc71 100%)',
                color: 'white'
              }}>
                <h2 style={{ 
                  margin: 0, 
                  fontSize: '22px', 
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <CheckCircle size={24} />
                  Сессия создана!
                </h2>
                <button 
                  className="btn-icon" 
                  onClick={handleCloseSuccessModal}
                  style={{
                    color: 'white',
                    padding: '6px',
                    borderRadius: '8px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <X size={20} />
                </button>
              </div>
              <div style={{
                padding: '28px',
                background: theme === 'dark' ? '#1e1e1e' : '#f8f9fa'
              }}>
                <div style={{
                  marginBottom: '20px',
                  padding: '16px',
                  background: theme === 'dark' ? '#3a3a3a' : 'white',
                  borderRadius: '12px',
                  border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
                }}>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: theme === 'dark' ? '#e0e0e0' : '#495057',
                    marginBottom: '8px'
                  }}>
                    Номер сессии
                  </div>
                  <div style={{
                    fontSize: '20px',
                    fontWeight: '700',
                    color: theme === 'dark' ? '#fff' : '#1a1a1a',
                    fontFamily: 'monospace'
                  }}>
                    #{createdSessionInfo.sessionId}
                  </div>
                </div>

                <div style={{
                  marginBottom: '20px',
                  padding: '16px',
                  background: theme === 'dark' ? '#3a3a3a' : 'white',
                  borderRadius: '12px',
                  border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
                }}>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: theme === 'dark' ? '#e0e0e0' : '#495057',
                    marginBottom: '8px'
                  }}>
                    Ссылка для кандидата
                  </div>
                  <div style={{
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center'
                  }}>
                    <code style={{
                      flex: 1,
                      padding: '10px 12px',
                      background: theme === 'dark' ? '#2d2d2d' : '#f8f9fa',
                      borderRadius: '8px',
                      fontSize: '13px',
                      color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
                      fontFamily: 'monospace',
                      wordBreak: 'break-all',
                      border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
                    }}>
                      {createdSessionInfo.tokenUrl}
                    </code>
                    <button
                      onClick={handleCopyTokenUrl}
                      style={{
                        padding: '10px 16px',
                        background: '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '14px',
                        fontWeight: '500',
                        transition: 'all 0.2s',
                        flexShrink: 0
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#5568d3'
                        e.currentTarget.style.transform = 'translateY(-1px)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#667eea'
                        e.currentTarget.style.transform = 'translateY(0)'
                      }}
                    >
                      <Copy size={16} />
                      Копировать
                    </button>
                  </div>
                </div>

                {linkCopied && (
                  <div style={{
                    padding: '12px 16px',
                    background: theme === 'dark' ? '#2d2d2d' : '#d4edda',
                    borderRadius: '8px',
                    border: `1px solid ${theme === 'dark' ? '#555' : '#28a745'}`,
                    fontSize: '13px',
                    color: theme === 'dark' ? '#e0e0e0' : '#155724',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    animation: 'fadeIn 0.3s ease-out'
                  }}>
                    <CheckCircle size={16} style={{ color: '#28a745' }} />
                    Ссылка скопирована! Отправьте её кандидату для доступа к сессии.
                  </div>
                )}

                <div style={{ 
                  display: 'flex', 
                  gap: '12px', 
                  justifyContent: 'flex-end',
                  paddingTop: '8px',
                  borderTop: theme === 'dark' ? '1px solid #444' : '1px solid #e9ecef'
                }}>
                  <button 
                    className="btn btn-secondary" 
                    onClick={handleCloseSuccessModal}
                    style={{
                      padding: '12px 24px',
                      fontSize: '15px',
                      fontWeight: '500'
                    }}
                  >
                    Закрыть
                  </button>
                  <button 
                    className="btn btn-primary" 
                    onClick={() => {
                      handleCloseSuccessModal()
                      navigate(`/reviewer/sessions/${createdSessionInfo.sessionId}`)
                    }}
                    style={{
                      padding: '12px 24px',
                      fontSize: '15px',
                      fontWeight: '500',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-1px)'
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    Открыть сессию
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {showCreateForm && (
          <div 
            className="modal" 
            onClick={() => setShowCreateForm(false)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              animation: 'fadeIn 0.2s ease-out'
            }}
          >
            <div 
              className="modal-content" 
              onClick={e => e.stopPropagation()}
              style={{
                background: theme === 'dark' ? '#2d2d2d' : 'white',
                borderRadius: '16px',
                width: '90%',
                maxWidth: '520px',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                animation: 'slideUp 0.3s ease-out',
                overflow: 'hidden'
              }}
            >
              <div style={{
                padding: '24px 28px',
                borderBottom: theme === 'dark' ? '1px solid #444' : '1px solid #e9ecef',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white'
              }}>
                <h2 style={{ 
                  margin: 0, 
                  fontSize: '22px', 
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <Plus size={24} />
                  Создать новую сессию
                </h2>
                <button 
                  className="btn-icon" 
                  onClick={() => setShowCreateForm(false)}
                  style={{
                    color: 'white',
                    padding: '6px',
                    borderRadius: '8px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  ✕
                </button>
              </div>
              <div style={{
                padding: '28px',
                background: theme === 'dark' ? '#1e1e1e' : '#f8f9fa'
              }}>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ 
                    display: 'block', 
                    marginBottom: '8px', 
                    fontWeight: '600',
                    fontSize: '14px',
                    color: theme === 'dark' ? '#e0e0e0' : '#495057'
                  }}>
                    Имя кандидата <span style={{ color: '#e74c3c' }}>*</span>
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newSession.candidate_name}
                    onChange={e => setNewSession({ ...newSession, candidate_name: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newSession.candidate_name.trim()) {
                        createSession()
                      }
                    }}
                    placeholder="Иван Иванов"
                    autoFocus
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      fontSize: '15px',
                      border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
                      borderRadius: '10px',
                      background: theme === 'dark' ? '#3a3a3a' : 'white',
                      color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
                      transition: 'all 0.2s',
                      fontFamily: 'inherit'
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = '#667eea'
                      e.currentTarget.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.15)'
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = theme === 'dark' ? '#555' : '#e9ecef'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  />
                </div>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ 
                    display: 'block', 
                    marginBottom: '8px', 
                    fontWeight: '600',
                    fontSize: '14px',
                    color: theme === 'dark' ? '#e0e0e0' : '#495057'
                  }}>
                    MR Package
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newSession.mr_package}
                    onChange={e => setNewSession({ ...newSession, mr_package: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newSession.candidate_name.trim()) {
                        createSession()
                      }
                    }}
                    placeholder="demo_package"
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      fontSize: '15px',
                      border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
                      borderRadius: '10px',
                      background: theme === 'dark' ? '#3a3a3a' : 'white',
                      color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
                      transition: 'all 0.2s',
                      fontFamily: 'inherit'
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = '#667eea'
                      e.currentTarget.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.15)'
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = theme === 'dark' ? '#555' : '#e9ecef'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  />
                </div>
                <div style={{ marginBottom: '24px' }}>
                  <label style={{ 
                    display: 'block', 
                    marginBottom: '8px', 
                    fontWeight: '600',
                    fontSize: '14px',
                    color: theme === 'dark' ? '#e0e0e0' : '#495057'
                  }}>
                    Проверяющий
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newSession.reviewer_name}
                    onChange={e => setNewSession({ ...newSession, reviewer_name: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newSession.candidate_name.trim()) {
                        createSession()
                      }
                    }}
                    placeholder="Reviewer"
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      fontSize: '15px',
                      border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
                      borderRadius: '10px',
                      background: theme === 'dark' ? '#3a3a3a' : 'white',
                      color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
                      transition: 'all 0.2s',
                      fontFamily: 'inherit'
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = '#667eea'
                      e.currentTarget.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.15)'
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = theme === 'dark' ? '#555' : '#e9ecef'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  />
                </div>
                <div style={{ 
                  display: 'flex', 
                  gap: '12px', 
                  justifyContent: 'flex-end',
                  paddingTop: '8px',
                  borderTop: theme === 'dark' ? '1px solid #444' : '1px solid #e9ecef'
                }}>
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => setShowCreateForm(false)}
                    style={{
                      padding: '12px 24px',
                      fontSize: '15px',
                      fontWeight: '500'
                    }}
                  >
                    Отмена
                  </button>
                  <button 
                    className="btn btn-primary" 
                    onClick={createSession} 
                    disabled={isLoading || !newSession.candidate_name.trim()}
                    style={{
                      padding: '12px 24px',
                      fontSize: '15px',
                      fontWeight: '500',
                      background: isLoading || !newSession.candidate_name.trim() 
                        ? '#ccc' 
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      border: 'none',
                      cursor: isLoading || !newSession.candidate_name.trim() ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      if (!isLoading && newSession.candidate_name.trim()) {
                        e.currentTarget.style.transform = 'translateY(-1px)'
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    {isLoading ? 'Создание...' : 'Создать'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div style={{ 
          maxWidth: '1200px', 
          width: '100%', 
          margin: '0 auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ 
            marginBottom: '24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h1 style={{ 
              margin: 0,
              fontSize: '28px',
              fontWeight: '600',
              color: '#1a1a1a'
            }}>
              Список сессий
            </h1>
            <div style={{ 
              fontSize: '14px', 
              color: '#666',
              background: '#f8f9fa',
              padding: '8px 16px',
              borderRadius: '8px'
            }}>
              Всего: {sessions.length}
            </div>
          </div>
          
          {sessions.length === 0 ? (
            <div className="card" style={{
              textAlign: 'center',
              padding: '60px 20px',
              background: 'white',
              borderRadius: '12px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}>
              <FileText size={48} style={{ color: '#ccc', marginBottom: '16px' }} />
              <p style={{ 
                color: '#666', 
                fontSize: '16px',
                margin: 0
              }}>
                Нет сессий. Создайте новую сессию для начала работы.
              </p>
            </div>
          ) : (
            <div style={{ 
              display: 'grid', 
              gap: '16px',
              flex: 1,
              overflowY: 'auto',
              paddingRight: '8px'
            }}>
              {sessions.map(session => (
                <div 
                  key={session.id} 
                  className="card"
                  onClick={() => navigate(`/reviewer/sessions/${session.id}`)}
                  style={{ 
                    cursor: 'pointer', 
                    transition: 'all 0.2s',
                    background: 'white',
                    borderRadius: '12px',
                    padding: '20px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                    border: '1px solid #e9ecef',
                    position: 'relative',
                    overflow: 'hidden'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f8f9fa'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.12)'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'white'
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'
                    e.currentTarget.style.transform = 'translateY(0)'
                  }}
                >
                  {/* Индикатор статуса */}
                  <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '4px',
                    background: session.status === 'active' 
                      ? 'linear-gradient(90deg, #27ae60, #2ecc71)' 
                      : session.status === 'expired'
                      ? '#e74c3c'
                      : '#95a5a6'
                  }} />
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: '16px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '12px',
                        marginBottom: '12px'
                      }}>
                        <h3 style={{ 
                          margin: 0,
                          fontSize: '20px',
                          fontWeight: '600',
                          color: '#1a1a1a'
                        }}>
                          Сессия #{session.id}
                        </h3>
                        {session.candidate_ready_at && (
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 8px',
                            background: '#d4edda',
                            color: '#155724',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '500',
                            border: '1px solid #c3e6cb'
                          }}>
                            <CheckCircle size={12} />
                            Готов
                          </span>
                        )}
                        {session.gitea?.enabled && (
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 8px',
                            background: '#e3f2fd',
                            color: '#1976d2',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '500'
                          }}>
                            <GitBranch size={12} />
                            Gitea
                          </span>
                        )}
                        {session.gitea?.pr_id && (
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 8px',
                            background: '#f3e5f5',
                            color: '#7b1fa2',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '500'
                          }}>
                            <GitMerge size={12} />
                            PR #{session.gitea.pr_id}
                          </span>
                        )}
                      </div>
                      
                      <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '12px',
                        color: '#666',
                        fontSize: '14px'
                      }}>
                        <div>
                          <div style={{ 
                            fontSize: '11px', 
                            textTransform: 'uppercase',
                            color: '#999',
                            marginBottom: '4px',
                            fontWeight: '500',
                            letterSpacing: '0.5px'
                          }}>
                            ID
                          </div>
                          <div style={{ fontWeight: '500', color: '#1a1a1a', fontFamily: 'monospace' }}>
                            #{session.id}
                          </div>
                        </div>
                        
                        <div>
                          <div style={{ 
                            fontSize: '11px', 
                            textTransform: 'uppercase',
                            color: '#999',
                            marginBottom: '4px',
                            fontWeight: '500',
                            letterSpacing: '0.5px'
                          }}>
                            Кандидат
                          </div>
                          <div style={{ fontWeight: '500', color: '#1a1a1a' }}>
                            {session.candidate_name || 'Unknown'}
                          </div>
                        </div>
                        
                        <div>
                          <div style={{ 
                            fontSize: '11px', 
                            textTransform: 'uppercase',
                            color: '#999',
                            marginBottom: '4px',
                            fontWeight: '500',
                            letterSpacing: '0.5px'
                          }}>
                            Создано
                          </div>
                          <div style={{ color: '#1a1a1a' }}>
                            {formatDate(session.created_at)}
                          </div>
                        </div>
                        
                        <div>
                          <div style={{ 
                            fontSize: '11px', 
                            textTransform: 'uppercase',
                            color: '#999',
                            marginBottom: '4px',
                            fontWeight: '500',
                            letterSpacing: '0.5px'
                          }}>
                            Истекает
                          </div>
                          <div style={{ color: '#1a1a1a' }}>
                            {formatDate(session.expires_at)}
                          </div>
                        </div>
                        
                        <div>
                          <div style={{ 
                            fontSize: '11px', 
                            textTransform: 'uppercase',
                            color: '#999',
                            marginBottom: '4px',
                            fontWeight: '500',
                            letterSpacing: '0.5px'
                          }}>
                            Комментарии
                          </div>
                          <div style={{ 
                            color: '#1a1a1a',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}>
                            <MessageSquare size={14} />
                            {session.comments?.length || 0}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ 
                      display: 'flex', 
                      gap: '8px',
                      flexShrink: 0
                    }}>
                      <button 
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation()
                          extendSession(session.id)
                        }}
                        style={{
                          padding: '8px',
                          minWidth: 'auto'
                        }}
                        title="Продлить на 30 минут"
                      >
                        <Timer size={16} />
                      </button>
                      <a
                        href={`${API_URL}/reviewer/sessions/${session.id}/report/pdf`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary"
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          padding: '8px',
                          minWidth: 'auto'
                        }}
                        title="Скачать PDF отчёт"
                      >
                        <FileText size={16} />
                      </a>
                      <button 
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSession(session.id, session.candidate_name)
                        }}
                        style={{
                          padding: '8px',
                          minWidth: 'auto',
                          color: '#e74c3c'
                        }}
                        title="Удалить сессию"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

