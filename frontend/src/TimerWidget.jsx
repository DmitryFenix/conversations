// frontend/src/TimerWidget.jsx
// Компонент для отображения таймера и прогресс-бара в отдельном окне
import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Clock, CheckCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = '/api'

export default function TimerWidget() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [isBlinking, setIsBlinking] = useState(false)
  const [notificationShown, setNotificationShown] = useState(false)
  const [isMarkingReady, setIsMarkingReady] = useState(false)
  const tickIntervalRef = useRef(null)
  const exitTimeoutRef = useRef(null)
  const audioContextRef = useRef(null)

  // Загрузка сессии
  useEffect(() => {
    if (!token) return
    
    const loadSession = async () => {
      try {
        const sessionRes = await axios.get(`${API_URL}/candidate/sessions/${token}`)
        setSession(sessionRes.data)
        
        // Сохраняем expires_at для таймера
        if (sessionRes.data.expires_at) {
          localStorage.setItem(`session_${sessionRes.data.session_id}`, JSON.stringify({
            expires_at: sessionRes.data.expires_at,
            created_at: sessionRes.data.created_at
          }))
        }
      } catch (err) {
        console.error('Failed to load session:', err)
      }
    }
    
    loadSession()
  }, [token])

  // Функция для звука "тик-так"
  const playTickSound = () => {
    if (!audioContextRef.current) {
      try {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      } catch (e) {
        return // Браузер не поддерживает Web Audio API
      }
    }
    
    try {
      const oscillator = audioContextRef.current.createOscillator()
      const gainNode = audioContextRef.current.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContextRef.current.destination)
      
      oscillator.frequency.value = 800
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.1, audioContextRef.current.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContextRef.current.currentTime + 0.1)
      
      oscillator.start(audioContextRef.current.currentTime)
      oscillator.stop(audioContextRef.current.currentTime + 0.1)
    } catch (e) {
      // Игнорируем ошибки звука
    }
  }

  // Функция для браузерных уведомлений
  const showBrowserNotification = (message) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Code Review Session', {
        body: message,
        icon: '/favicon.svg'
      })
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification('Code Review Session', {
            body: message,
            icon: '/favicon.svg'
          })
        }
      })
    }
  }

  // Отметить готовность
  const markReady = async () => {
    if (!session || !token) return
    
    setIsMarkingReady(true)
    try {
      await axios.post(`${API_URL}/candidate/sessions/${token}/ready`)
      // Обновляем сессию
      const sessionRes = await axios.get(`${API_URL}/candidate/sessions/${token}`)
      setSession(sessionRes.data)
    } catch (err) {
      console.error('Failed to mark ready:', err)
    } finally {
      setIsMarkingReady(false)
    }
  }

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

      const timerEl = document.getElementById('timer-widget-timer')
      if (timerEl) timerEl.textContent = timeStr

      const progressEl = document.getElementById('timer-widget-progress')
      if (progressEl) {
        const total = 2 * 60 * 60 * 1000 // 2 часа в миллисекундах
        const percent = (diff / total) * 100
        progressEl.style.width = `${Math.max(0, percent)}%`
        
        // Цвет по оставшемуся времени
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
          // Сессия истекла
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

  if (!session) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        padding: '20px',
        background: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <Clock size={32} style={{ color: '#666', marginBottom: '12px' }} />
          <p style={{ color: '#666' }}>Загрузка сессии...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      minWidth: '320px',
      maxWidth: '400px',
      padding: '20px',
      background: 'white',
      borderRadius: '12px',
      boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ 
          margin: '0 0 8px 0', 
          fontSize: '18px', 
          fontWeight: '600',
          color: '#2c3e50'
        }}>
          Code Review Session
        </h3>
        <p style={{ 
          margin: 0, 
          fontSize: '14px', 
          color: '#666' 
        }}>
          {session.candidate_name || 'Кандидат'}
        </p>
      </div>

      {/* ТАЙМЕР + ПРОГРЕСС-БАР */}
      <div 
        id="timer-widget-container"
        style={{
          fontSize: '13px',
          fontFamily: 'monospace',
          background: 'rgba(0,0,0,0.05)',
          padding: '12px 16px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          transition: 'all 0.3s ease',
          animation: isBlinking ? 'blink 1s infinite' : 'none',
          marginBottom: '20px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontWeight: 'bold' }}>
          <Clock size={16} style={{ color: '#666' }} />
          <span style={{ flex: 1 }}>Осталось времени сессии</span>
          <span 
            id="timer-widget-timer" 
            style={{ 
              color: '#2c3e50', 
              fontFamily: 'monospace',
              fontSize: '16px',
              fontWeight: '600'
            }}
          >
            2:00:00
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '12px',
          background: '#ddd',
          borderRadius: '6px',
          overflow: 'hidden',
          border: '1px solid #ccc'
        }}>
          <div
            id="timer-widget-progress"
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

      {/* Кнопка "Готово" */}
      {session.candidate_ready_at ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '12px 16px',
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
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '12px 16px',
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

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}

