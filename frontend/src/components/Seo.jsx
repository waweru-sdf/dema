import { useEffect } from 'react'

const SUFFIX = 'Dr. Feysel Dermatology Specialized Clinic'

// The server already sends the right title and structured data for the first page load.
// This keeps the browser tab title and description correct when visitors move between pages.
export default function Seo({ title, description }) {
  useEffect(() => {
    document.title = title ? `${title} | ${SUFFIX}` : SUFFIX
    let tag = document.querySelector('meta[name="description"]')
    if (!tag) {
      tag = document.createElement('meta')
      tag.setAttribute('name', 'description')
      document.head.appendChild(tag)
    }
    if (description) tag.setAttribute('content', description)
  }, [title, description])
  return null
}
