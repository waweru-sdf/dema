import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import PostCard from '../components/PostCard'
import Seo from '../components/Seo'
import { ErrorState, Loading } from '../components/States'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

export default function Blog() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') || ''
  const [q, setQ] = useState('')
  const { data, error, loading } = useFetch(() => api.posts({ category }), [category])
  const needle = q.trim().toLowerCase()
  const posts = (data?.posts || []).filter((p) => !needle || `${p.title} ${p.excerpt} ${p.category}`.toLowerCase().includes(needle))
  return (
    <>
      <Seo title="Blog" description="Skin, hair and nail health articles from the doctors at Dr. Feysel Dermatology Specialized Clinic in Addis Ababa." />
      <Hero eyebrow="Blog" title="Our blog" intro="Skin, hair and nail health articles from our doctors." />
      <div className="wrap py-12">
        <div className="mx-auto mb-6 max-w-xl">
          <label className="relative block">
            <span className="sr-only">Search articles</span>
            <Icon name="search" size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
            <input type="search" className="input !rounded-full !pl-11" placeholder="Search articles…" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
        </div>
        {data && data.categories.length > 1 && (
          <div className="mb-9 flex flex-wrap justify-center gap-2" role="group" aria-label="Filter by type">
            <button className={`chip ${!category ? 'chip-on' : ''}`} onClick={() => setParams({})}>All</button>
            {data.categories.map((c) => <button key={c} className={`chip ${category === c ? 'chip-on' : ''}`} aria-pressed={category === c} onClick={() => setParams({ category: c })}>{c}</button>)}
          </div>
        )}
        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {data && (posts.length
          ? <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{posts.map((p) => <PostCard key={p.slug} post={p} />)}</div>
          : <p className="text-center text-muted">{data.posts.length ? 'No articles match your search.' : 'No articles yet. Please check back soon.'}</p>)}
      </div>
    </>
  )
}
