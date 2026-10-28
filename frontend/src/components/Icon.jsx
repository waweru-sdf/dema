import {
  ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, CalendarCheck, Gem, Target, BadgeCheck, CircleAlert, CircleCheck, ChevronDown, Clock, CreditCard, Droplets,
  Eye, GraduationCap, ImagePlus, Languages, Mail, MapPin, Menu, MessageCircle, Phone, Quote, Scissors,
  Search, ShieldCheck, Sparkles, Sprout, Star, Stethoscope, Sun, UserPlus, Video, X, Zap,
} from 'lucide-react'

const ICONS = {
  'arrow-left': ArrowLeft, 'book-open': BookOpen, 'calendar-check': CalendarCheck, gem: Gem, target: Target,
  'arrow-right': ArrowRight, 'arrow-up-right': ArrowUpRight, 'badge-check': BadgeCheck, 'circle-alert': CircleAlert,
  'circle-check': CircleCheck, 'chevron-down': ChevronDown, clock: Clock, 'credit-card': CreditCard, droplets: Droplets,
  eye: Eye, 'graduation-cap': GraduationCap, 'image-plus': ImagePlus, languages: Languages, mail: Mail, 'map-pin': MapPin,
  menu: Menu, 'message-circle': MessageCircle, phone: Phone, quote: Quote, scissors: Scissors, search: Search,
  'shield-check': ShieldCheck, sparkles: Sparkles, sprout: Sprout, star: Star, stethoscope: Stethoscope, sun: Sun,
  'user-plus': UserPlus, video: Video, x: X, zap: Zap,
}

export default function Icon({ name, size = 18, className = '', ...rest }) {
  const Cmp = ICONS[name]
  return Cmp ? <Cmp size={size} className={className} aria-hidden="true" {...rest} /> : null
}
