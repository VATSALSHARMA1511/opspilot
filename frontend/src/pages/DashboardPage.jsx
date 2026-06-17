import { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import client from '../api/client'
import { Ticket, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line
} from 'recharts'

const STATUS_COLORS = {
  open: '#facc15',
  assigned: '#60a5fa',
  in_progress: '#a78bfa',
  resolved: '#4ade80',
  closed: '#71717a',
}

const PRIORITY_COLORS = {
  low: '#4ade80',
  medium: '#facc15',
  high: '#f97316',
  critical: '#ef4444',
}

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-xs text-white">
        {label && <p className="text-zinc-400 mb-1">{label}</p>}
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color || p.fill }}>{p.name}: <span className="text-white font-medium">{p.value}</span></p>
        ))}
      </div>
    )
  }
  return null
}

export default function DashboardPage() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    client.get('/api/v1/tickets?page_size=100').then(res => {
      setTickets(res.data.items || [])
    }).finally(() => setLoading(false))
  }, [])

  // Stat counts
  const counts = {
    total: tickets.length,
    open: tickets.filter(t => t.status === 'open').length,
    in_progress: tickets.filter(t => t.status === 'in_progress').length,
    resolved: tickets.filter(t => t.status === 'resolved').length,
  }

  const stats = [
    { label: 'Total Tickets', value: counts.total, icon: Ticket, color: 'text-blue-400' },
    { label: 'Open', value: counts.open, icon: AlertCircle, color: 'text-yellow-400' },
    { label: 'In Progress', value: counts.in_progress, icon: Clock, color: 'text-purple-400' },
    { label: 'Resolved', value: counts.resolved, icon: CheckCircle, color: 'text-green-400' },
  ]

  // Donut — tickets by status
  const statusData = Object.entries(
    tickets.reduce((acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1
      return acc
    }, {})
  ).map(([name, value]) => ({ name, value }))

  // Bar — tickets by priority
  const priorityOrder = ['low', 'medium', 'high', 'critical']
  const priorityData = priorityOrder
    .map(p => ({
      name: p.charAt(0).toUpperCase() + p.slice(1),
      value: tickets.filter(t => t.priority === p).length,
      fill: PRIORITY_COLORS[p],
    }))
    .filter(p => p.value > 0)

  // Line — tickets created per day (last 30 days)
  const last30 = Array.from({ length: 30 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (29 - i))
    return d.toISOString().split('T')[0]
  })

  const createdByDay = tickets.reduce((acc, t) => {
    const day = t.created_at?.split('T')[0]
    if (day) acc[day] = (acc[day] || 0) + 1
    return acc
  }, {})

  const lineData = last30.map(date => ({
    date: date.slice(5), // MM-DD
    tickets: createdByDay[date] || 0,
  }))

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-white">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-1">Overview of your IT tickets</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-zinc-500 text-xs">{label}</span>
              <Icon size={16} className={color} />
            </div>
            <span className="text-2xl font-semibold text-white">
              {loading ? '–' : value}
            </span>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      {!loading && (
        <div className="grid grid-cols-3 gap-4 mb-8">

          {/* Donut — Status */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-sm font-medium text-white mb-4">Tickets by Status</p>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {statusData.map((entry) => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#71717a'} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
              {statusData.map(entry => (
                <div key={entry.name} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: STATUS_COLORS[entry.name] || '#71717a' }} />
                  <span className="text-xs text-zinc-400">{entry.name} ({entry.value})</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar — Priority */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-sm font-medium text-white mb-4">Tickets by Priority</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={priorityData} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#27272a' }} />
                <Bar dataKey="value" name="Tickets" radius={[4, 4, 0, 0]}>
                  {priorityData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Line — Created over time */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-sm font-medium text-white mb-4">Tickets Created (Last 30 Days)</p>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval={6}
                />
                <YAxis tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="tickets"
                  name="Tickets"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#60a5fa' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

        </div>
      )}

      {/* Recent Tickets */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
        <div className="px-4 py-3 border-b border-zinc-800">
          <span className="text-sm font-medium text-white">Recent Tickets</span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-zinc-600 text-sm">Loading...</div>
        ) : tickets.length === 0 ? (
          <div className="p-8 text-center text-zinc-600 text-sm">No tickets yet</div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {tickets.slice(0, 5).map(ticket => (
              <div key={ticket.id} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">{ticket.title}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{ticket.created_by?.full_name}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border
                  ${ticket.status === 'open' ? 'border-yellow-800 text-yellow-400' :
                    ticket.status === 'resolved' ? 'border-green-800 text-green-400' :
                    'border-zinc-700 text-zinc-400'}`}>
                  {ticket.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}