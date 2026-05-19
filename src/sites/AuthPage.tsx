import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { APIError, postAPI } from "../fetchAPI"

type RegisterPayload = {
  name: string
  lastname: string
  username: string
  email: string
  password: string
}

type LoginResponse = {
  access_token: string
  token_type: string
}

const cardClass = "rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"

const AuthPage = () => {
  const navigate = useNavigate()
  const [message, setMessage] = useState<string>("")
  const [error, setError] = useState<string>("")

  const [register, setRegister] = useState<RegisterPayload>({
    name: "",
    lastname: "",
    username: "",
    email: "",
    password: "",
  })

  const [login, setLogin] = useState({ username: "", password: "" })

  async function handleRegister(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("")
    setMessage("")
    try {
      const res = await postAPI<{ message: string }>("/api/register", register)
      setMessage(res.message)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Register failed")
    }
  }

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("")
    setMessage("")
    try {
      const body = new URLSearchParams({
        username: login.username,
        password: login.password,
      })
      const res = await postAPI<LoginResponse>("/api/login", body, { credentials: "include" })
      localStorage.setItem("access_token", res.access_token)
      navigate("/home")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Login failed")
    }
  }

  async function handleRefresh() {
    setError("")
    setMessage("")
    try {
      const res = await postAPI<LoginResponse>("/api/refresh", undefined, { credentials: "include" })
      localStorage.setItem("access_token", res.access_token)
      setMessage("Token refreshed")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Refresh failed")
    }
  }

  return (
    <section className="mx-auto grid max-w-6xl gap-4 md:grid-cols-2">
      <form className={cardClass} onSubmit={handleLogin}>
        <h2 className="mb-3 text-xl font-semibold text-slate-900">Login</h2>
        <div className="space-y-3">
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Username"
            value={login.username}
            onChange={(e) => {
              const value = e.currentTarget.value
              setLogin((v) => ({ ...v, username: value }))
            }}
          />
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Password"
            type="password"
            value={login.password}
            onChange={(e) => {
              const value = e.currentTarget.value
              setLogin((v) => ({ ...v, password: value }))
            }}
          />
          <div className="flex gap-2">
            <button className="rounded-lg bg-slate-900 px-3 py-2 text-white" type="submit">
              Login
            </button>
            <button
              className="rounded-lg border border-slate-300 px-3 py-2 text-slate-700"
              type="button"
              onClick={handleRefresh}
            >
              Refresh Token
            </button>
          </div>
        </div>
      </form>

      <form className={cardClass} onSubmit={handleRegister}>
        <h2 className="mb-3 text-xl font-semibold text-slate-900">Register</h2>
        <div className="space-y-3">
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Name" value={register.name} onChange={(e) => {
            const value = e.currentTarget.value
            setRegister((v) => ({ ...v, name: value }))
          }} />
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Lastname" value={register.lastname} onChange={(e) => {
            const value = e.currentTarget.value
            setRegister((v) => ({ ...v, lastname: value }))
          }} />
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Username" value={register.username} onChange={(e) => {
            const value = e.currentTarget.value
            setRegister((v) => ({ ...v, username: value }))
          }} />
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Email" type="email" value={register.email} onChange={(e) => {
            const value = e.currentTarget.value
            setRegister((v) => ({ ...v, email: value }))
          }} />
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Password" type="password" value={register.password} onChange={(e) => {
            const value = e.currentTarget.value
            setRegister((v) => ({ ...v, password: value }))
          }} />
          <button className="rounded-lg bg-slate-900 px-3 py-2 text-white" type="submit">
            Register
          </button>
        </div>
      </form>

      {(message || error) && (
        <div className="md:col-span-2">
          <p className={error ? "text-red-600" : "text-emerald-700"}>{error || message}</p>
        </div>
      )}
    </section>
  )
}

export default AuthPage
