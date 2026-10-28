import { ErrorState, Loading } from '../components/States'
import ConcernTile from '../components/ConcernTile'
import Hero from '../components/Hero'
import SearchBox from '../components/SearchBox'
import Seo from '../components/Seo'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

export default function Conditions() {
  const { data, error, loading } = useFetch(() => api.conditions(), [])
  return (
    <>
      <Seo title="Skin, hair and nail conditions" description="Patient guides to acne, vitiligo, psoriasis, skin cancer screening, hair loss and eczema, with the doctors who treat them." />
      <Hero eyebrow="Conditions" title="What can we help you with?" intro="Plain-language guides, each linked to the doctors who treat the condition.">
        <SearchBox className="mt-7 max-w-xl" />
      </Hero>
      <div className="wrap py-12">
        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {data && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.conditions.map((c) => <ConcernTile key={c.slug} condition={c} />)}</div>}
      </div>
    </>
  )
}
