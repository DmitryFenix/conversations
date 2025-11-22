// frontend/src/MRSelectionPage.jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowRight, Sparkles, ChevronDown } from 'lucide-react'
import axios from 'axios'
import MRSelector from './MRSelector'
import './MRSelectionPage.css'

const API_URL = '/api'

export default function MRSelectionPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') ?? 'light')
  const [session, setSession] = useState(null)
  const [selectedMRIds, setSelectedMRIds] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [showScrollHint, setShowScrollHint] = useState(true)

  // Скрываем подсказку о прокрутке после первого скролла
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 100) {
        setShowScrollHint(false)
      }
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Синхронизация темы и включение скролла
  useEffect(() => {
    document.body.classList.toggle('dark', theme === 'dark')
    
    // Добавляем класс для переопределения стилей через CSS
    document.body.classList.add('mr-selection-page')
    document.documentElement.classList.add('mr-selection-page')
    const root = document.getElementById('root')
    if (root) {
      root.classList.add('mr-selection-page')
    }
    
    // Также устанавливаем inline стили для надежности
    document.body.style.overflow = 'auto'
    document.body.style.height = 'auto'
    document.documentElement.style.overflow = 'auto'
    document.documentElement.style.height = 'auto'
    if (root) {
      root.style.height = 'auto'
      root.style.overflow = 'auto'
    }
    
    const handleStorageChange = () => {
      const newTheme = localStorage.getItem('theme') ?? 'light'
      setTheme(newTheme)
    }
    window.addEventListener('storage', handleStorageChange)
    // Проверяем тему при монтировании
    const currentTheme = localStorage.getItem('theme') ?? 'light'
    setTheme(currentTheme)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      // Убираем классы при размонтировании
      document.body.classList.remove('mr-selection-page')
      document.documentElement.classList.remove('mr-selection-page')
      if (root) {
        root.classList.remove('mr-selection-page')
      }
    }
  }, [theme])

  useEffect(() => {
    loadSession()
  }, [sessionId])

  const loadSession = async () => {
    try {
      const res = await axios.get(`${API_URL}/reviewer/sessions/${sessionId}`)
      setSession(res.data)
      // Если уже выбраны MR, загружаем их
      if (res.data.mr_id) {
        setSelectedMRIds([res.data.mr_id])
      }
      setIsLoading(false)
    } catch (err) {
      console.error('Ошибка загрузки сессии:', err)
      setIsLoading(false)
    }
  }

  const handleMRSelectionChange = (mrIds) => {
    setSelectedMRIds(mrIds)
  }

  const handleContinue = async () => {
    if (selectedMRIds.length === 0) {
      // Можно продолжить без MR (будет использован demo diff)
      navigate(`/reviewer/sessions/${sessionId}`)
      return
    }

    setIsSaving(true)
    try {
      // Обновляем сессию с выбранными MR
      await axios.put(`${API_URL}/reviewer/sessions/${sessionId}/mrs`, {
        mr_ids: selectedMRIds
      })
      
      // Перенаправляем на страницу сессии
      navigate(`/reviewer/sessions/${sessionId}`)
    } catch (err) {
      console.error('Ошибка сохранения MR:', err)
      alert('Ошибка сохранения выбранных MR. Попробуйте снова.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSkip = () => {
    // Пропускаем выбор MR, переходим к сессии
    navigate(`/reviewer/sessions/${sessionId}`)
  }

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: theme === 'dark' ? '#1a1a1a' : '#f8f9fa'
      }}>
        <div style={{
          fontSize: '18px',
          color: theme === 'dark' ? '#e0e0e0' : '#495057'
        }}>
          Загрузка...
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: theme === 'dark' ? '#1a1a1a' : '#f8f9fa'
      }}>
        <div style={{
          fontSize: '18px',
          color: '#e74c3c'
        }}>
          Сессия не найдена
        </div>
      </div>
    )
  }

  return (
    <div 
      className="mr-selection-page-container"
      style={{
        minHeight: '100vh',
        width: '100%',
        background: theme === 'dark' ? '#1a1a1a' : '#f8f9fa',
        padding: '40px 20px 180px 20px', // Увеличен padding-bottom для fixed кнопок
        position: 'relative',
        display: 'block'
      }}>
      <div style={{
        maxWidth: '1200px',
        width: '100%',
        margin: '0 auto',
        position: 'relative',
        paddingBottom: '40px' // Дополнительный отступ внизу
      }}>
        {/* Заголовок - Sticky при скролле */}
        <div style={{
          marginBottom: '32px',
          textAlign: 'center',
          position: 'sticky',
          top: '0',
          zIndex: 10,
          background: theme === 'dark' ? '#1a1a1a' : '#f8f9fa',
          paddingTop: '20px',
          paddingBottom: '20px',
          backdropFilter: 'blur(10px)',
          borderBottom: `1px solid ${theme === 'dark' ? 'rgba(85, 85, 85, 0.3)' : 'rgba(233, 236, 239, 0.5)'}`
        }}>
          <h1 style={{
            fontSize: '32px',
            fontWeight: '700',
            margin: '0 0 12px 0',
            color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px'
          }}>
            <Sparkles size={32} style={{ color: '#667eea' }} />
            Выбор Merge Requests для сессии
          </h1>
          <p style={{
            fontSize: '16px',
            color: theme === 'dark' ? '#999' : '#666',
            margin: 0
          }}>
            Сессия для кандидата: <strong>{session.candidate_name}</strong>
          </p>
        </div>

        {/* Информация о сессии */}
        <div style={{
          background: theme === 'dark' ? '#2d2d2d' : 'white',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '32px',
          border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
          boxShadow: theme === 'dark' ? 'none' : '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px'
          }}>
            <div>
              <div style={{
                fontSize: '12px',
                color: theme === 'dark' ? '#999' : '#666',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Кандидат
              </div>
              <div style={{
                fontSize: '16px',
                fontWeight: '600',
                color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
              }}>
                {session.candidate_name}
              </div>
            </div>
            <div>
              <div style={{
                fontSize: '12px',
                color: theme === 'dark' ? '#999' : '#666',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Сессия
              </div>
              <div style={{
                fontSize: '16px',
                fontWeight: '600',
                color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
              }}>
                #{session.id}
              </div>
            </div>
            <div>
              <div style={{
                fontSize: '12px',
                color: theme === 'dark' ? '#999' : '#666',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Статус
              </div>
              <div style={{
                fontSize: '16px',
                fontWeight: '600',
                color: session.status === 'active' ? '#2ecc71' : '#999'
              }}>
                {session.status === 'active' ? 'Активна' : session.status}
              </div>
            </div>
          </div>
        </div>

        {/* Подсказка о прокрутке вниз */}
        {showScrollHint && (
          <div style={{
            textAlign: 'center',
            marginBottom: '20px',
            padding: '12px',
            background: theme === 'dark' ? 'rgba(102, 126, 234, 0.1)' : 'rgba(102, 126, 234, 0.05)',
            borderRadius: '8px',
            border: `1px solid ${theme === 'dark' ? 'rgba(102, 126, 234, 0.3)' : 'rgba(102, 126, 234, 0.2)'}`,
            animation: 'pulse 2s infinite',
            cursor: 'pointer'
          }}
          onClick={() => {
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
            setShowScrollHint(false)
          }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              color: theme === 'dark' ? '#667eea' : '#667eea',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              <ChevronDown size={16} />
              <span>Прокрутите вниз, чтобы увидеть кнопки навигации</span>
              <ChevronDown size={16} />
            </div>
          </div>
        )}

        {/* Компонент выбора MR */}
        <MRSelector
          selectedMRIds={selectedMRIds}
          onSelectionChange={handleMRSelectionChange}
          theme={theme}
        />

        {/* Кнопки действий - Fixed внизу экрана */}
        <div style={{
          display: 'flex',
          gap: '16px',
          justifyContent: 'flex-end',
          marginTop: '32px',
          paddingTop: '24px',
          paddingBottom: '24px',
          position: 'fixed',
          bottom: '0',
          left: '0',
          right: '0',
          zIndex: 100,
          background: theme === 'dark' ? 'rgba(26, 26, 26, 0.95)' : 'rgba(248, 249, 250, 0.95)',
          backdropFilter: 'blur(20px)',
          paddingLeft: '20px',
          paddingRight: '20px',
          boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.1)',
          borderTop: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
        }}>
          <div style={{
            maxWidth: '1200px',
            width: '100%',
            margin: '0 auto',
            display: 'flex',
            gap: '16px',
            justifyContent: 'flex-end'
          }}>
          <button
            onClick={handleSkip}
            disabled={isSaving}
            style={{
              padding: '14px 28px',
              fontSize: '16px',
              fontWeight: '500',
              background: 'transparent',
              color: theme === 'dark' ? '#999' : '#666',
              border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
              borderRadius: '10px',
              cursor: isSaving ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              opacity: isSaving ? 0.5 : 1
            }}
            onMouseEnter={(e) => {
              if (!isSaving) {
                e.currentTarget.style.background = theme === 'dark' ? '#3a3a3a' : '#f8f9fa'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
            }}
          >
            Пропустить (использовать demo)
          </button>
          <button
            onClick={handleContinue}
            disabled={isSaving}
            style={{
              padding: '14px 32px',
              fontSize: '16px',
              fontWeight: '600',
              background: isSaving
                ? '#ccc'
                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              cursor: isSaving ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: isSaving ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.3)'
            }}
            onMouseEnter={(e) => {
              if (!isSaving) {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.4)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = isSaving ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.3)'
            }}
          >
            {isSaving ? 'Сохранение...' : 'Продолжить'}
            {!isSaving && <ArrowRight size={20} />}
          </button>
          </div>
        </div>
      </div>
    </div>
  )
}
