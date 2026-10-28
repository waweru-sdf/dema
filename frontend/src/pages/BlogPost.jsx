import { Link, useParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import { InPersonLink, TeleButton } from '../components/Buttons'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import PostCard from '../components/PostCard'
import RichText from '../components/RichText'
import Seo from '../components/Seo'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'
import { formatDate } from '../lib/format'
import NotFound from './NotFound'

export default function BlogPost() {
  const { slug } = useParams()
  const { data, error, loading } = useFetch(() => api.post(slug), [slug])
  if (error?.status === 404) return <NotFound />
  if (loading) return <><Hero title="" /><Loading /></>
  if (error) return <><Hero title="" /><ErrorState error={error} /></>
  const p = data.post
  return (
    <>
      <Seo title={p.title} description={p.excerpt.slice(0, 158)} />
      <Hero eyebrow={p.category} title={p.title}>
        <p className="mt-5 text-sm text-[#cfe3f5]">
          <Link to="/" className="hover:text-white">Home</Link> / <Link to="/blog" className="hover:text-white">Blog</Link> · {formatDate(p.date)} · {p.read_minutes} min read
        </p>
      </Hero>
      <article className="wrap max-w-3xl py-12">
        {p.image && <img src={p.image} alt="" className="mb-9 aspect-[16/10] w-full rounded-[28px] object-cover" />}
        <RichText text={p.body} />
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/blog" className="btn btn-outline"><Icon name="arrow-left" size={16} /> All articles</Link>
          <TeleButton />
          <InPersonLink className="btn btn-outline">Book in person</InPersonLink>
        </div>
      </article>
      {data.more.length > 0 && (
        <section className="bg-[#E8F1F9] py-12">
          <div className="wrap">
            <p className="text-center text-xs font-bold uppercase tracking-[.14em] text-leaf">Keep reading</p>
            <h2 className="mb-7 mt-1 text-center text-3xl">More articles</h2>
            <div className="grid gap-6 md:grid-cols-3">{data.more.map((m) => <PostCard key={m.slug} post={m} />)}</div>
          </div>
        </section>
      )}
    </>
  )
}
