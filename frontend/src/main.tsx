import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './lib/auth.tsx'
import WakeBanner from './components/WakeBanner.tsx'
import { ensureAwake } from './lib/wake.ts'

ensureAwake() // start waking the backend as soon as the page opens, before anything asks for data

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <WakeBanner />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
