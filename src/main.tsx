import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {BrowserRouter} from "react-router-dom"
import {QueryClientProvider, QueryClient} from "@tanstack/react-query"
import './index.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
})
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter >
    <QueryClientProvider client ={queryClient}> 
      <App />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)
