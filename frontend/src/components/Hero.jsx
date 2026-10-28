// Dark blue band that starts at the very top of every page, behind the floating navigation pill.
export default function Hero({ eyebrow, title, intro, children, side, className = '', tall = false }) {
  return (
    <section className={`relative overflow-hidden bg-hero-blue text-white ${className}`}>
      <div className="pointer-events-none absolute -right-36 -top-52 h-[640px] w-[640px] rounded-full bg-[radial-gradient(circle,rgba(124,194,66,.35),transparent_65%)]" />
      <div className={`wrap relative ${tall ? 'pb-16 pt-36 lg:pb-20' : 'pb-12 pt-32 lg:pb-16 lg:pt-36'}`}>
        <div className={side ? 'grid items-center gap-10 lg:grid-cols-[1.15fr_1fr]' : ''}>
          <div>
            {eyebrow && <span className="pill pill-dark">{eyebrow}</span>}
            <h1 className="mt-4 text-4xl leading-[1.05] text-white sm:text-5xl lg:text-6xl">{title}</h1>
            {intro && <p className="mt-4 max-w-2xl text-lg leading-relaxed text-[#cfe3f5]">{intro}</p>}
            {children}
          </div>
          {side}
        </div>
      </div>
    </section>
  )
}
