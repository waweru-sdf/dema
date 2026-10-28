import { Link } from 'react-router-dom'
import Hero from '../components/Hero'
import Seo from '../components/Seo'

export default function NotFound() {
  return (
    <>
      <Seo title="Page not found" />
      <Hero eyebrow="404" title="We could not find that page" intro="The page may have moved. Try one of these instead." />
      <div className="wrap flex flex-wrap gap-3 py-12">
        <Link to="/" className="btn btn-primary">Home</Link>
        <Link to="/doctors" className="btn btn-outline">Our doctors</Link>
        <Link to="/conditions" className="btn btn-outline">Conditions</Link>
      </div>
    </>
  )
}
