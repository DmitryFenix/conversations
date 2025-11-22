// frontend/src/router.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ReviewerDashboard from './ReviewerDashboard.jsx'
import MRSelectionPage from './MRSelectionPage.jsx'
import CandidateView from './CandidateView.jsx'
import TimerWidget from './TimerWidget.jsx'
import LegacyApp from './App.jsx'

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Новые роуты с разделением ролей */}
        <Route path="/reviewer" element={<ReviewerDashboard />} />
        <Route path="/reviewer/sessions/:sessionId/select-mr" element={<MRSelectionPage />} />
        <Route path="/reviewer/sessions/:sessionId" element={<ReviewerDashboard />} />
        <Route path="/candidate/:token" element={<CandidateView />} />
        <Route path="/timer/:token" element={<TimerWidget />} />
        
        {/* Редирект корневого URL на reviewer */}
        <Route path="/" element={<Navigate to="/reviewer" replace />} />
        
        {/* Старый роут для обратной совместимости (по старому пути) */}
        <Route path="/legacy" element={<LegacyApp />} />
        
        {/* Редирект всех остальных на reviewer */}
        <Route path="*" element={<Navigate to="/reviewer" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

