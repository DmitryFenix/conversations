import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import ReactDOM from 'react-dom/client'
import './index.css'
import AppRouter from './router.jsx'

const root = ReactDOM.createRoot(document.getElementById('root'))
root.render(
  <StrictMode>
    <AppRouter />
  </StrictMode>
)

// Apply saved theme
const savedTheme = localStorage.getItem('theme')
if (savedTheme === 'dark') {
  document.body.classList.add('dark')
}