import { ErrorState, Loading } from '../components/States'
import Hero from '../components/Hero'
import Seo from '../components/Seo'
import ServiceTabs from '../components/ServiceTabs'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

export default function Services() {
  const { data, error, loading } = useFetch(() => api.services(), [])
  return (
    <>
      <Seo title="Services" description="Hair and scalp, aesthetic dermatology, dermatosurgery, laser treatments and PRP at our Bole and Zenebework branches." />
      <Hero eyebrow="At the clinic" title="Services" intro="Online visits cover consultations, follow-ups and prescriptions. Procedures such as transplants, lasers and surgery are done in person." />
      <div className="wrap py-12">
        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {data && <ServiceTabs services={data.services} />}
      </div>
    </>
  )
}
