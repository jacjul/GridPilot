import { useEffect, useState } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import Header from "./components/Header.tsx"
import AuthPage from "./sites/AuthPage.tsx"
import Home from "./sites/Home.tsx"
import Stammdaten from "./sites/Stammdaten.tsx"
import ProfilePage from "./sites/ProfilePage.tsx"
import OptimizationPage from "./sites/OptimizationPage.tsx"
import "./App.css"

function isAuthenticated() {
  return Boolean(localStorage.getItem("access_token"))
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  return <>{children}</>
}

function App() {
  const [, setAuthTick] = useState(0)

  useEffect(() => {
    const onSessionExpired = () => {
      setAuthTick((value) => value + 1)
    }

    window.addEventListener("auth:session-expired", onSessionExpired)
    return () => window.removeEventListener("auth:session-expired", onSessionExpired)
  }, [])

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
