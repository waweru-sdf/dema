// All requests to the Flask backend live here so pages never build URLs by hand.
async function request(path, options) {
  const res = await fetch(path, { headers: { Accept: 'application/json' }, ...options })
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    const err = new Error((data && data.message) || 'Something went wrong. Please try again.')
    err.status = res.status
    err.errors = (data && data.errors) || {}
    throw err
  }
  return data
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body) })

const query = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return q ? `?${q}` : ''
}

export const api = {
  settings: () => request('/api/site/settings'),
  home: () => request('/api/site/home'),
  services: () => request('/api/site/services'),
  doctors: (params) => request(`/api/site/doctors${query(params)}`),
  doctor: (slug) => request(`/api/site/doctors/${slug}`),
  conditions: () => request('/api/site/conditions'),
  condition: (slug) => request(`/api/site/conditions/${slug}`),
  reviews: (params) => request(`/api/site/reviews${query(params)}`),
  submitReview: (body) => post('/api/site/reviews', body),
  gallery: () => request('/api/site/gallery'),
  meta: () => request('/api/meta'),
  availability: (params) => request(`/api/availability${query(params)}`),
  book: (body) => post('/api/appointments', body),
  posts: (params) => request(`/api/site/posts${query(params)}`),
  post: (slug) => request(`/api/site/posts/${slug}`),
  search: (q) => request(`/api/site/search${query({ q })}`),
  contact: (body) => post('/api/contact', body),
}
