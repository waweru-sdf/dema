export function Loading({ label = 'Loading' }) {
  return (
    <div className="wrap py-24 text-center text-muted" role="status">
      <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-line border-t-leaf" />
      {label}…
    </div>
  )
}

export function ErrorState({ error }) {
  return (
    <div className="wrap py-24 text-center">
      <h2 className="mb-2 text-2xl">We could not load this page</h2>
      <p className="text-muted">{error?.message || 'Please check your connection and try again.'}</p>
      <button className="btn btn-primary mt-6" onClick={() => window.location.reload()}>Try again</button>
    </div>
  )
}
