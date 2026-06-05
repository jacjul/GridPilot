import { getAccessToken, setAccessToken } from "./authStore"

export class APIError extends Error {
    statusCode: number
    details?: unknown

    constructor(statusCode: number, message: string, details?: unknown) {
        super(message)
        this.name = "APIError"
        this.statusCode = statusCode
        this.details = details
    }
}

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

export type APIOptions = {
    method?: HttpMethod
    headers?: HeadersInit
    token?: string
    body?: BodyInit | Record<string, unknown>
    timeoutMs?: number
    signal?: AbortSignal
    credentials?: RequestCredentials
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ""
const SESSION_EXPIRED_EVENT = "auth:session-expired"
let refreshInFlight: Promise<string | null> | null = null

function createTimeoutSignal(timeoutMs: number): AbortSignal {
    const controller = new AbortController()
    setTimeout(() => controller.abort(), timeoutMs)
    return controller.signal
}

function mergeSignals(a?: AbortSignal, b?: AbortSignal): AbortSignal | undefined {
    if (!a) return b
    if (!b) return a

    const controller = new AbortController()
    const abort = () => controller.abort()

    if (a.aborted || b.aborted) {
        controller.abort()
        return controller.signal
    }

    a.addEventListener("abort", abort, { once: true })
    b.addEventListener("abort", abort, { once: true })
    return controller.signal
}

function buildUrl(path: string): string {
    const base = API_BASE_URL.replace(/\/$/, "")
    const route = path.startsWith("/") ? path : `/${path}`
    return `${base}${route}`
}

function getCookieValue(name: string): string | null {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
    return match ? decodeURIComponent(match[1]) : null
}

function needsCsrfHeader(path: string, method: HttpMethod): boolean {
    if (method !== "POST") {
        return false
    }
    return path === "/api/refresh" || path === "/api/logout"
}

export async function requestAPI<T>(path: string, options: APIOptions = {}): Promise<T> {
    const {
        method = "GET",
        headers,
        token,
        body,
        timeoutMs = 10000,
        signal,
        credentials,
    } = options

    const resolvedToken = token || getAccessToken() || undefined
    const timeoutSignal = createTimeoutSignal(timeoutMs)
    const mergedSignal = mergeSignals(signal, timeoutSignal)
    const csrfToken = getCookieValue("csrf_token")

    const buildHeaders = (accessToken?: string): HeadersInit => ({
        ...(body && !(body instanceof FormData) && !(body instanceof URLSearchParams)
            ? { "Content-Type": "application/json" }
            : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(csrfToken && needsCsrfHeader(path, method) ? { "X-CSRF-Token": csrfToken } : {}),
        ...(headers ?? {}),
    })

    const finalBody =
        body && !(body instanceof FormData) && !(body instanceof URLSearchParams)
            ? JSON.stringify(body)
            : body

    async function fetchWithToken(accessToken?: string): Promise<Response> {
        try {
            return await fetch(buildUrl(path), {
            method,
            headers: buildHeaders(accessToken),
            body: finalBody,
            signal: mergedSignal,
            credentials,
        })
        } catch (error) {
            if (error instanceof DOMException && error.name === "AbortError") {
                throw new APIError(408, "Request timed out or was cancelled")
            }
            throw error
        }
    }

    async function refreshAccessToken(): Promise<string | null> {
        if (refreshInFlight) {
            return refreshInFlight
        }

        refreshInFlight = (async () => {
        try {
            const refreshCsrfToken = getCookieValue("csrf_token")
            const response = await fetch(buildUrl("/api/refresh"), {
                method: "POST",
                headers: refreshCsrfToken ? { "X-CSRF-Token": refreshCsrfToken } : undefined,
                credentials: credentials ?? "include",
            })

            if (!response.ok) {
                return null
            }

            const payload = await response.json() as { access_token?: string }
            const newToken = payload.access_token
            if (!newToken) {
                return null
            }
            setAccessToken(newToken)
            return newToken
        } catch {
            return null
        } finally {
            refreshInFlight = null
        }
        })()

        return refreshInFlight
    }

    let response = await fetchWithToken(resolvedToken)

    // If access token is expired, try one silent refresh and retry once.
    if (response.status === 401 && resolvedToken) {
        const refreshedToken = await refreshAccessToken()
        if (refreshedToken) {
            response = await fetchWithToken(refreshedToken)
        } else {
            setAccessToken(null)
            window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
        }
    }

    const contentType = response.headers.get("content-type") ?? ""
    const isJsonResponse = contentType.includes("application/json")

    const payload =
        response.status === 204
            ? null
            : isJsonResponse
                ? await response.json()
                : await response.text()

    if (!response.ok) {
        const message =
            typeof payload === "object" && payload && "detail" in payload
                ? String((payload as { detail: unknown }).detail)
                : "Request failed"

        throw new APIError(response.status, message, payload)
    }

    return payload as T
}

export function getAPI<T>(path: string, options: Omit<APIOptions, "method" | "body"> = {}) {
    return requestAPI<T>(path, { ...options, method: "GET" })
}

export function postAPI<T>(
    path: string,
    body?: BodyInit | Record<string, unknown>,
    options: Omit<APIOptions, "method" | "body"> = {}
) {
    return requestAPI<T>(path, { ...options, method: "POST", body })
}

export function putAPI<T>(
    path: string,
    body?: BodyInit | Record<string, unknown>,
    options: Omit<APIOptions, "method" | "body"> = {}
) {
    return requestAPI<T>(path, { ...options, method: "PUT", body })
}

export function patchAPI<T>(
    path: string,
    body?: BodyInit | Record<string, unknown>,
    options: Omit<APIOptions, "method" | "body"> = {}
) {
    return requestAPI<T>(path, { ...options, method: "PATCH", body })
}

export function deleteAPI<T>(
    path: string,
    options: Omit<APIOptions, "method" | "body"> = {}
) {
    return requestAPI<T>(path, { ...options, method: "DELETE" })
}
