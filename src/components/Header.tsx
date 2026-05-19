import { Link, useNavigate } from "react-router-dom"
import { postAPI } from "../fetchAPI"

const navClass = "text-sm font-medium text-slate-700 hover:text-slate-900"

const Header = () => {
  const navigate = useNavigate()
  const isAuthed = Boolean(localStorage.getItem("access_token"))

  async function handleLogout() {
    try {
      await postAPI<{ message: string }>("/api/logout", undefined, {
        token: localStorage.getItem("access_token") ?? "",
        credentials: "include",
      })
    } catch {
      // Ignore API errors, still clear local auth state.
    } finally {
      localStorage.removeItem("access_token")
      navigate("/auth")
    }
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 md:px-6">
        <span className="text-base font-semibold text-slate-900">GridPilot</span>
        <div className="flex items-center gap-4">
          {isAuthed ? (
            <>
              <Link className={navClass} to="/home">
                Home
              </Link>
              <Link className={navClass} to="/stammdaten">
                Stammdaten
              </Link>
              <Link className={navClass} to="/profile">
                Profile
              </Link>
              <Link className={navClass} to="/optimization">
                Optimization
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-lg border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
              >
                Logout
              </button>
            </>
          ) : (
            <Link className={navClass} to="/auth">
              Login / Register
            </Link>
          )}
        </div>
      </nav>
    </header>
  )
}

export default Header
