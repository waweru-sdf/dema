import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from './Icon'

// Searches conditions, doctors and articles (see pages/Search.jsx).
export default function SearchBox({ className = '', placeholder = 'Acne, vitiligo, hair loss, skin check…' }) {
  const [q, setQ] = useState('')
  const navigate = useNavigate()
  const submit = (e) => {
    e.preventDefault()
    if (q.trim().length >= 2) navigate(`/search?q=${encodeURIComponent(q.trim())}`)
  }
  return (
    <form onSubmit={submit} role="search" className={`glass flex items-center gap-3 rounded-full p-1.5 pl-5 ${className}`}>
      <Icon name="search" size={20} className="shrink-0 text-[#cfe3f5]" />
      <label className="sr-only" htmlFor="site-search">Search the website</label>
      <input id="site-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder}
        className="min-w-0 flex-1 bg-transparent py-2 text-white outline-none placeholder:text-[#cfe3f5]/80" />
      <button className="btn btn-lime shrink-0" type="submit">Find</button>
    </form>
  )
}
