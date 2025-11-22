// frontend/src/MRSelector.jsx
import { useState, useEffect } from 'react'
import { Search, Filter, CheckCircle2, Circle, Sparkles, Tag, X } from 'lucide-react'
import axios from 'axios'
import './MRSelector.css'

const API_URL = '/api'

const MR_TYPE_LABELS = {
  bugfix: 'Bugfix',
  feature: 'Feature',
  refactoring: 'Refactoring',
  tests: 'Tests',
  performance: 'Performance',
  security: 'Security',
  infrastructure: 'Infrastructure',
  code_style: 'Code Style'
}

const MR_TYPE_COLORS = {
  bugfix: '#e74c3c',
  feature: '#3498db',
  refactoring: '#9b59b6',
  tests: '#2ecc71',
  performance: '#f39c12',
  security: '#e67e22',
  infrastructure: '#1abc9c',
  code_style: '#95a5a6'
}

const GRADE_RANGES = {
  junior: { min: 3, max: 4, label: 'Junior (3-4 балла)' },
  middle: { min: 5, max: 7, label: 'Middle (5-7 баллов)' },
  senior: { min: 8, max: 10, label: 'Senior (8-10 баллов)' }
}

export default function MRSelector({ selectedMRIds = [], onSelectionChange, theme = 'light' }) {
  const [mrs, setMrs] = useState([])
  const [recommendedMrs, setRecommendedMrs] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    mr_type: '',
    min_points: '',
    max_points: '',
    stack_tag: ''
  })
  const [targetGrade, setTargetGrade] = useState('')
  const [showRecommendations, setShowRecommendations] = useState(false)
  const [totalPoints, setTotalPoints] = useState(0)

  // Загрузка списка MR
  useEffect(() => {
    loadMRs()
  }, [filters])

  // Обновление выбранных баллов
  useEffect(() => {
    if (selectedMRIds.length > 0 && mrs.length > 0) {
      const selected = mrs.filter(mr => selectedMRIds.includes(mr.id))
      const points = selected.reduce((sum, mr) => sum + (mr.complexity_points || 3), 0)
      setTotalPoints(points)
    } else {
      setTotalPoints(0)
    }
  }, [selectedMRIds, mrs])

  const loadMRs = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.mr_type) params.append('mr_type', filters.mr_type)
      if (filters.min_points) params.append('min_complexity_points', filters.min_points)
      if (filters.max_points) params.append('max_complexity_points', filters.max_points)
      if (filters.stack_tag) params.append('stack_tag', filters.stack_tag)
      params.append('limit', '100')

      const res = await axios.get(`${API_URL}/mr/list?${params.toString()}`)
      setMrs(res.data.merge_requests || [])
    } catch (err) {
      console.error('Ошибка загрузки MR:', err)
      setMrs([])
    } finally {
      setIsLoading(false)
    }
  }

  const getRecommendations = async () => {
    if (!targetGrade) return

    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('target_grade', targetGrade)
      if (filters.stack_tag) params.append('stack_tags', filters.stack_tag)

      const res = await axios.get(`${API_URL}/mr/recommend?${params.toString()}`)
      setRecommendedMrs(res.data.recommended_mrs || [])
      setShowRecommendations(true)
    } catch (err) {
      console.error('Ошибка получения рекомендаций:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleMR = (mrId) => {
    const newSelection = selectedMRIds.includes(mrId)
      ? selectedMRIds.filter(id => id !== mrId)
      : [...selectedMRIds, mrId]
    onSelectionChange(newSelection)
  }

  const selectRecommended = () => {
    const recommendedIds = recommendedMrs.map(mr => mr.id)
    onSelectionChange(recommendedIds)
  }

  const clearFilters = () => {
    setFilters({ mr_type: '', min_points: '', max_points: '', stack_tag: '' })
    setSearchQuery('')
    setTargetGrade('')
    setShowRecommendations(false)
  }

  const filteredMrs = mrs.filter(mr => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const title = (mr.title || '').toLowerCase()
      const description = (mr.description || '').toLowerCase()
      if (!title.includes(query) && !description.includes(query)) {
        return false
      }
    }
    return true
  })

  const selectedMrs = mrs.filter(mr => selectedMRIds.includes(mr.id))
  const currentGradeRange = targetGrade ? GRADE_RANGES[targetGrade] : null

  return (
    <div style={{
      border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
      borderRadius: '12px',
      padding: '20px',
      background: theme === 'dark' ? '#2d2d2d' : '#f8f9fa',
      marginBottom: '20px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '20px'
      }}>
        <Sparkles size={20} style={{ color: '#667eea' }} />
        <h3 style={{
          margin: 0,
          fontSize: '18px',
          fontWeight: '600',
          color: theme === 'dark' ? '#e0e0e0' : '#495057'
        }}>
          Выбор Merge Requests
        </h3>
      </div>

      {/* Прогресс-бар выбранных баллов */}
      {selectedMRIds.length > 0 && (
        <div style={{
          marginBottom: '20px',
          padding: '16px',
          background: theme === 'dark' ? '#3a3a3a' : 'white',
          borderRadius: '10px',
          border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px'
          }}>
            <span style={{
              fontSize: '14px',
              fontWeight: '600',
              color: theme === 'dark' ? '#e0e0e0' : '#495057'
            }}>
              Выбрано: {selectedMRIds.length} MR, {totalPoints} баллов
            </span>
            {currentGradeRange && (
              <span style={{
                fontSize: '12px',
                color: totalPoints >= currentGradeRange.min && totalPoints <= currentGradeRange.max
                  ? '#2ecc71' : '#e74c3c',
                fontWeight: '500'
              }}>
                {currentGradeRange.label}
              </span>
            )}
          </div>
          {currentGradeRange && (
            <div style={{
              width: '100%',
              height: '8px',
              background: theme === 'dark' ? '#444' : '#e9ecef',
              borderRadius: '4px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${Math.min(100, (totalPoints / currentGradeRange.max) * 100)}%`,
                height: '100%',
                background: totalPoints >= currentGradeRange.min && totalPoints <= currentGradeRange.max
                  ? 'linear-gradient(90deg, #2ecc71, #27ae60)'
                  : 'linear-gradient(90deg, #e74c3c, #c0392b)',
                transition: 'width 0.3s ease'
              }} />
            </div>
          )}
        </div>
      )}

      {/* Рекомендации */}
      <div style={{
        marginBottom: '20px',
        padding: '16px',
        background: theme === 'dark' ? '#3a3a3a' : 'white',
        borderRadius: '10px',
        border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
      }}>
        <div style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '12px',
          flexWrap: 'wrap'
        }}>
          <select
            value={targetGrade}
            onChange={(e) => setTargetGrade(e.target.value)}
            style={{
              flex: 1,
              minWidth: '150px',
              padding: '10px 12px',
              fontSize: '14px',
              border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
              borderRadius: '8px',
              background: theme === 'dark' ? '#3a3a3a' : 'white',
              color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
              cursor: 'pointer'
            }}
          >
            <option value="">Выберите грейд</option>
            {Object.entries(GRADE_RANGES).map(([key, range]) => (
              <option key={key} value={key}>{range.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Теги стека (python, backend)"
            value={filters.stack_tag}
            onChange={(e) => setFilters({ ...filters, stack_tag: e.target.value })}
            style={{
              flex: 1,
              minWidth: '150px',
              padding: '10px 12px',
              fontSize: '14px',
              border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
              borderRadius: '8px',
              background: theme === 'dark' ? '#3a3a3a' : 'white',
              color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
            }}
          />
          <button
            onClick={getRecommendations}
            disabled={!targetGrade || isLoading}
            style={{
              padding: '10px 20px',
              background: targetGrade && !isLoading ? '#667eea' : '#95a5a6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: targetGrade && !isLoading ? 'pointer' : 'not-allowed',
              fontSize: '14px',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            <Sparkles size={16} />
            Рекомендации
          </button>
        </div>

        {showRecommendations && recommendedMrs.length > 0 && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            background: theme === 'dark' ? '#2d2d2d' : '#f8f9fa',
            borderRadius: '8px',
            border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '13px',
                fontWeight: '600',
                color: theme === 'dark' ? '#e0e0e0' : '#495057'
              }}>
                Рекомендуемые MR:
              </span>
              <button
                onClick={selectRecommended}
                style={{
                  padding: '6px 12px',
                  background: '#2ecc71',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: '500'
                }}
              >
                Выбрать все
              </button>
            </div>
            <div 
              className="mr-selector-scroll"
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                maxHeight: '200px',
                overflowY: 'auto',
                padding: '4px',
                scrollBehavior: 'smooth'
              }}>
              {recommendedMrs.map(mr => {
                const isSelected = selectedMRIds.includes(mr.id)
                const mrType = mr.mr_type || 'feature'
                return (
                  <span
                    key={mr.id}
                    style={{
                      padding: '6px 12px',
                      background: isSelected 
                        ? '#667eea' 
                        : (theme === 'dark' ? '#3a3a3a' : '#e9ecef'),
                      color: isSelected 
                        ? 'white' 
                        : (theme === 'dark' ? '#e0e0e0' : '#495057'),
                      borderRadius: '8px',
                      fontSize: '12px',
                      fontWeight: '500',
                      cursor: 'pointer',
                      border: `2px solid ${isSelected ? '#667eea' : (theme === 'dark' ? '#555' : '#ddd')}`,
                      transition: 'all 0.2s',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: isSelected ? '0 2px 6px rgba(102, 126, 234, 0.3)' : '0 1px 3px rgba(0,0,0,0.1)'
                    }}
                    onClick={() => toggleMR(mr.id)}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.transform = 'translateY(-2px)'
                        e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)'
                        e.currentTarget.style.borderColor = '#667eea'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)'
                        e.currentTarget.style.borderColor = theme === 'dark' ? '#555' : '#ddd'
                      }
                    }}
                  >
                    <span style={{
                      padding: '2px 6px',
                      background: isSelected ? 'rgba(255,255,255,0.2)' : MR_TYPE_COLORS[mrType] || '#95a5a6',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '600'
                    }}>
                      {MR_TYPE_LABELS[mrType] || mrType}
                    </span>
                    <span>{mr.title?.substring(0, 25)}...</span>
                    <span style={{
                      padding: '2px 6px',
                      background: isSelected ? 'rgba(255,255,255,0.2)' : (theme === 'dark' ? '#555' : '#ddd'),
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '600'
                    }}>
                      ⭐ {mr.complexity_points || 3}
                    </span>
                  </span>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Фильтры */}
      <div style={{
        marginBottom: '20px',
        padding: '16px',
        background: theme === 'dark' ? '#3a3a3a' : 'white',
        borderRadius: '10px',
        border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '12px'
        }}>
          <Filter size={16} style={{ color: '#667eea' }} />
          <span style={{
            fontSize: '14px',
            fontWeight: '600',
            color: theme === 'dark' ? '#e0e0e0' : '#495057'
          }}>
            Фильтры
          </span>
          {(filters.mr_type || filters.min_points || filters.max_points || filters.stack_tag || searchQuery) && (
            <button
              onClick={clearFilters}
              style={{
                marginLeft: 'auto',
                padding: '4px 8px',
                background: 'transparent',
                border: 'none',
                color: '#e74c3c',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <X size={14} />
              Очистить
            </button>
          )}
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '12px'
        }}>
          <select
            value={filters.mr_type}
            onChange={(e) => setFilters({ ...filters, mr_type: e.target.value })}
            style={{
              padding: '10px 12px',
              fontSize: '14px',
              border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
              borderRadius: '8px',
              background: theme === 'dark' ? '#3a3a3a' : 'white',
              color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
              cursor: 'pointer'
            }}
          >
            <option value="">Все типы</option>
            {Object.entries(MR_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="number"
              placeholder="Мин. баллы"
              min="1"
              max="5"
              value={filters.min_points}
              onChange={(e) => setFilters({ ...filters, min_points: e.target.value })}
              style={{
                flex: 1,
                padding: '10px 12px',
                fontSize: '14px',
                border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
                borderRadius: '8px',
                background: theme === 'dark' ? '#3a3a3a' : 'white',
                color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
              }}
            />
            <input
              type="number"
              placeholder="Макс. баллы"
              min="1"
              max="5"
              value={filters.max_points}
              onChange={(e) => setFilters({ ...filters, max_points: e.target.value })}
              style={{
                flex: 1,
                padding: '10px 12px',
                fontSize: '14px',
                border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
                borderRadius: '8px',
                background: theme === 'dark' ? '#3a3a3a' : 'white',
                color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
              }}
            />
          </div>
        </div>
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{
            position: 'absolute',
            left: '12px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#999'
          }} />
          <input
            type="text"
            placeholder="Поиск по названию или описанию..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 36px',
              fontSize: '14px',
              border: `2px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
              borderRadius: '8px',
              background: theme === 'dark' ? '#3a3a3a' : 'white',
              color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
            }}
          />
        </div>
      </div>

      {/* Список MR */}
      <div 
        className="mr-selector-scroll"
        style={{
          maxHeight: '600px',
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '8px',
          background: theme === 'dark' ? '#2d2d2d' : 'white',
          borderRadius: '10px',
          border: `1px solid ${theme === 'dark' ? '#555' : '#e9ecef'}`,
          scrollBehavior: 'smooth',
          // Кастомный скроллбар для Firefox
          scrollbarWidth: 'thin',
          scrollbarColor: theme === 'dark' ? '#555 #2d2d2d' : '#cbd5e0 #ffffff'
        }}>
        {isLoading ? (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#999'
          }}>
            Загрузка...
          </div>
        ) : filteredMrs.length === 0 ? (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#999'
          }}>
            MR не найдены
          </div>
        ) : (
          filteredMrs.map(mr => {
            const isSelected = selectedMRIds.includes(mr.id)
            const mrType = mr.mr_type || 'feature'
            return (
              <div
                key={mr.id}
                onClick={() => toggleMR(mr.id)}
                style={{
                  padding: '16px',
                  marginBottom: '8px',
                  background: isSelected
                    ? (theme === 'dark' ? '#3a3a3a' : '#e8f4f8')
                    : (theme === 'dark' ? '#2d2d2d' : 'white'),
                  border: `2px solid ${isSelected ? '#667eea' : (theme === 'dark' ? '#555' : '#e9ecef')}`,
                  borderRadius: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.borderColor = '#667eea'
                    e.currentTarget.style.background = theme === 'dark' ? '#3a3a3a' : '#f8f9fa'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.borderColor = theme === 'dark' ? '#555' : '#e9ecef'
                    e.currentTarget.style.background = theme === 'dark' ? '#2d2d2d' : 'white'
                  }
                }}
              >
                <div style={{
                  marginTop: '2px',
                  cursor: 'pointer'
                }}>
                  {isSelected ? (
                    <CheckCircle2 size={20} style={{ color: '#667eea' }} />
                  ) : (
                    <Circle size={20} style={{ color: '#999' }} />
                  )}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '6px',
                    flexWrap: 'wrap'
                  }}>
                    <span style={{
                      fontSize: '15px',
                      fontWeight: '600',
                      color: theme === 'dark' ? '#e0e0e0' : '#1a1a1a'
                    }}>
                      {mr.title || `MR #${mr.id}`}
                    </span>
                    <span 
                      onClick={(e) => {
                        e.stopPropagation()
                        // Фильтруем по типу при клике
                        setFilters({ ...filters, mr_type: mrType })
                      }}
                      style={{
                        padding: '4px 10px',
                        background: MR_TYPE_COLORS[mrType] || '#95a5a6',
                        color: 'white',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: '600',
                        textTransform: 'uppercase',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        boxShadow: `0 1px 3px rgba(0,0,0,0.2)`,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-1px) scale(1.05)'
                        e.currentTarget.style.boxShadow = `0 3px 8px rgba(0,0,0,0.3)`
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0) scale(1)'
                        e.currentTarget.style.boxShadow = `0 1px 3px rgba(0,0,0,0.2)`
                      }}
                      title={`Нажмите для фильтрации по типу: ${MR_TYPE_LABELS[mrType] || mrType}`}
                    >
                      {MR_TYPE_LABELS[mrType] || mrType}
                    </span>
                    <span style={{
                      padding: '4px 8px',
                      background: theme === 'dark' ? '#3a3a3a' : '#f8f9fa',
                      color: theme === 'dark' ? '#e0e0e0' : '#495057',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '600',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      ⭐ {mr.complexity_points || 3} баллов
                    </span>
                  </div>
                  {mr.description && (
                    <div style={{
                      fontSize: '13px',
                      color: theme === 'dark' ? '#999' : '#666',
                      marginBottom: '8px',
                      lineHeight: '1.5'
                    }}>
                      {mr.description.substring(0, 150)}
                      {mr.description.length > 150 ? '...' : ''}
                    </div>
                  )}
                  <div style={{
                    display: 'flex',
                    gap: '8px',
                    flexWrap: 'wrap',
                    marginTop: '8px'
                  }}>
                    {mr.stack_tags && mr.stack_tags.length > 0 && mr.stack_tags.map(tag => {
                      // Определяем цвет тега на основе его значения
                      const getTagColor = (tagName) => {
                        const tagLower = tagName.toLowerCase()
                        if (tagLower.includes('python')) return { bg: '#3776ab', color: '#fff', icon: '🐍' }
                        if (tagLower.includes('javascript') || tagLower.includes('js')) return { bg: '#f7df1e', color: '#000', icon: '📜' }
                        if (tagLower.includes('typescript') || tagLower.includes('ts')) return { bg: '#3178c6', color: '#fff', icon: '📘' }
                        if (tagLower.includes('react')) return { bg: '#61dafb', color: '#000', icon: '⚛️' }
                        if (tagLower.includes('vue')) return { bg: '#4fc08d', color: '#fff', icon: '💚' }
                        if (tagLower.includes('node') || tagLower.includes('backend')) return { bg: '#339933', color: '#fff', icon: '🟢' }
                        if (tagLower.includes('frontend')) return { bg: '#ff6b6b', color: '#fff', icon: '🎨' }
                        if (tagLower.includes('database') || tagLower.includes('sql')) return { bg: '#336791', color: '#fff', icon: '🗄️' }
                        if (tagLower.includes('docker')) return { bg: '#2496ed', color: '#fff', icon: '🐳' }
                        if (tagLower.includes('kubernetes') || tagLower.includes('k8s')) return { bg: '#326ce5', color: '#fff', icon: '☸️' }
                        if (tagLower.includes('api')) return { bg: '#ff6b35', color: '#fff', icon: '🔌' }
                        if (tagLower.includes('test')) return { bg: '#28a745', color: '#fff', icon: '🧪' }
                        return { bg: theme === 'dark' ? '#667eea' : '#667eea', color: '#fff', icon: '🏷️' }
                      }
                      const tagStyle = getTagColor(tag)
                      return (
                        <span
                          key={tag}
                          onClick={(e) => {
                            e.stopPropagation()
                            // Фильтруем по тегу при клике
                            setFilters({ ...filters, stack_tag: tag })
                          }}
                          style={{
                            padding: '4px 10px',
                            background: tagStyle.bg,
                            color: tagStyle.color,
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '500',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            border: `1px solid ${tagStyle.bg}`,
                            boxShadow: `0 1px 3px rgba(0,0,0,0.1)`
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-1px) scale(1.05)'
                            e.currentTarget.style.boxShadow = `0 3px 8px rgba(0,0,0,0.2)`
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0) scale(1)'
                            e.currentTarget.style.boxShadow = `0 1px 3px rgba(0,0,0,0.1)`
                          }}
                          title={`Нажмите для фильтрации по тегу: ${tag}`}
                        >
                          <span style={{ fontSize: '12px' }}>{tagStyle.icon}</span>
                          <span style={{ textTransform: 'capitalize' }}>{tag}</span>
                        </span>
                      )
                    })}
                    {mr.language && (
                      <span 
                        onClick={(e) => {
                          e.stopPropagation()
                          // Фильтруем по языку при клике
                          setFilters({ ...filters, stack_tag: mr.language })
                        }}
                        style={{
                          padding: '4px 10px',
                          background: theme === 'dark' ? '#667eea' : '#667eea',
                          color: '#fff',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: '500',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          border: `1px solid ${theme === 'dark' ? '#667eea' : '#667eea'}`,
                          boxShadow: `0 1px 3px rgba(0,0,0,0.1)`,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-1px) scale(1.05)'
                          e.currentTarget.style.boxShadow = `0 3px 8px rgba(0,0,0,0.2)`
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'translateY(0) scale(1)'
                          e.currentTarget.style.boxShadow = `0 1px 3px rgba(0,0,0,0.1)`
                        }}
                        title={`Нажмите для фильтрации по языку: ${mr.language}`}
                      >
                        💻 {mr.language}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}



