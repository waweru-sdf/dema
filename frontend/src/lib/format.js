export const formatDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

export const telHref = (phone) => `tel:${String(phone).replace(/[^\d+]/g, '')}`

export const money = (n) => `ETB ${Number(n).toLocaleString('en-US')}`

export const initials = (name = '') =>
  name.replace(/^Dr\.?\s+/i, '').split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase()

// Links to the telemedicine service (Tena Medicine). The doctor is passed along so the patient lands with them selected.
export function teleLink(baseUrl, doctorSlug) {
  try {
    const url = new URL(baseUrl, window.location.origin)
    url.searchParams.set('source', 'drfeysel')
    if (doctorSlug) url.searchParams.set('doctor', doctorSlug)
    return url.toString()
  } catch {
    return baseUrl
  }
}

export const isExternal = (href) => /^https?:\/\//i.test(href) && !href.startsWith(window.location.origin)
