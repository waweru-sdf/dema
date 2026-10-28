import { useEffect } from 'react'
import { Outlet, Route, Routes, useLocation } from 'react-router-dom'
import Footer from './components/Footer'
import Nav from './components/Nav'
import { SiteProvider } from './context/SiteContext'
import About from './pages/About'
import Appointment from './pages/Appointment'
import Blog from './pages/Blog'
import BlogPost from './pages/BlogPost'
import ConditionPage from './pages/ConditionPage'
import Conditions from './pages/Conditions'
import Contact from './pages/Contact'
import DoctorProfile from './pages/DoctorProfile'
import Doctors from './pages/Doctors'
import Home from './pages/Home'
import NotFound from './pages/NotFound'
import Reviews from './pages/Reviews'
import Search from './pages/Search'
import Services from './pages/Services'
import Telemedicine from './pages/Telemedicine'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function Layout() {
  return (
    <>
      <a href="#content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-full focus:bg-white focus:px-4 focus:py-2">Skip to content</a>
      <ScrollToTop />
      <Nav />
      <main id="content"><Outlet /></main>
      <Footer />
    </>
  )
}

export default function App() {
  return (
    <SiteProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="about" element={<About />} />
          <Route path="appointment" element={<Appointment />} />
          <Route path="doctors" element={<Doctors />} />
          <Route path="doctors/:slug" element={<DoctorProfile />} />
          <Route path="conditions" element={<Conditions />} />
          <Route path="conditions/:slug" element={<ConditionPage />} />
          <Route path="services" element={<Services />} />
          <Route path="telemedicine" element={<Telemedicine />} />
          <Route path="reviews" element={<Reviews />} />
          <Route path="blog" element={<Blog />} />
          <Route path="blog/:slug" element={<BlogPost />} />
          <Route path="contact" element={<Contact />} />
          <Route path="search" element={<Search />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </SiteProvider>
  )
}
