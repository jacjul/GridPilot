import { useEffect, useState } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import Header from "./components/Header.tsx"
import AuthPage from "./sites/AuthPage.tsx"
import Home from "./sites/Home.tsx"
import Stammdaten from "./sites/Stammdaten.tsx"
import ProfilePage from "./sites/ProfilePage.tsx"
import OptimizationPage from "./sites/OptimizationPage.tsx"
import { getAccessToken, setAccessToken } from "./authStore"
import { postAPI } from "./fetchAPI"
import "./App.css"

type LoginResponse = {
  access_token: string
  token_type: string
}

function isAuthenticated() {
  return Boolean(getAccessToken())
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  return <>{children}</>
}

function App() {
  const [, setAuthTick] = useState(0)
  const [isAuthReady, setIsAuthReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function bootstrapAuth() {
      if (getAccessToken()) {
        if (!cancelled) {
          setIsAuthReady(true)
        }
        return
      }

      try {
        const res = await postAPI<LoginResponse>("/api/refresh", undefined, {
          credentials: "include",
          timeoutMs: 8000,
        })
        if (!cancelled) {
          setAccessToken(res.access_token)
        }
      } catch {
        if (!cancelled) {
          setAccessToken(null)
        }
      } finally {
        if (!cancelled) {
          setAuthTick((value) => value + 1)
          setIsAuthReady(true)
        }
      }
    }

    bootstrapAuth()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const onSessionExpired = () => {
      setAuthTick((value) => value + 1)
    }

    window.addEventListener("auth:session-expired", onSessionExpired)
    return () => window.removeEventListener("auth:session-expired", onSessionExpired)
  }, [])

  if (!isAuthReady) {
    return (
      <main className="p-4 md:p-6">
        <p className="text-sm text-slate-600">Restoring session...</p>
      </main>
    )
  }

  return (
    <>
      <Header />
      <main className="p-4 md:p-6">
        <Routes>
          <Route path="/" element={<Navigate to={isAuthenticated() ? "/home" : "/auth"} replace />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route
            path="/home"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stammdaten"
            element={
              <ProtectedRoute>
                <Stammdaten />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/optimization"
            element={
              <ProtectedRoute>
                <OptimizationPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </>
  )
}

export default App
