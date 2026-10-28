import { Link, useSearchParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import ConcernTile from '../components/ConcernTile'
import DoctorCard from '../components/DoctorCard'
import Hero from '../components/Hero'
import PostCard from '../components/PostCard'
import SearchBox from '../components/SearchBox'
import Seo from '../components/Seo'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

export default function Search() {
  const [params] = useSearchParams()
  const q = params.get('q') || ''
  const { data, error, loading } = useFetch(() => api.search(q), [q])
  const empty = data && !data.conditions.length && !data.doctors.length && !data.posts.length
  return (
    <>
      <Seo title={q ? `Search: ${q}` : 'Search'} description="Search conditions, doctors and articles." />
      <Hero eyebrow="Search" title={q ? `Results for “${q}”` : 'Search the website'}><SearchBox className="mt-7 max-w-xl" /></Hero>
      <div className="wrap space-y-12 py-12">
        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {empty && <p className="card p-8 text-muted">Nothing matched “{q}”. Try a simpler word such as acne, hair or mole, or <Link className="font-semibold text-royal" to="/conditions">browse all conditions</Link>.</p>}
        {data?.conditions.length > 0 && <section><h2 className="mb-5 text-3xl">Conditions</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.conditions.map((c) => <ConcernTile key={c.slug} condition={c} />)}</div></section>}
        {data?.doctors.length > 0 && <section><h2 className="mb-5 text-3xl">Doctors</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{data.doctors.map((d) => <DoctorCard key={d.slug} doctor={d} height="h-[360px]" />)}</div></section>}
        {data?.posts.length > 0 && <section><h2 className="mb-5 text-3xl">Articles</h2><div className="grid gap-5 md:grid-cols-3">{data.posts.map((p) => <PostCard key={p.slug} post={p} />)}</div></section>}
      </div>
    </>
  )
}
