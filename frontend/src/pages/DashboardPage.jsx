import { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import client from '../api/client'
import { Ticket, CheckCircle, Clock, AlertCircle } from 'lucide-react'

export default function DashboardPage() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    client.get('/api/v1/tickets').then(res => {
      setTickets(res.data.items || [])
    }).finally(() => setLoading(false))
  }, [])

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

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-white">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-1">Overview of your IT tickets</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-zinc-500 text-xs">{label}</span>
              <Icon size={16} className={color} />
            </div>
            <span className="text-2xl font-semibold text-white">
              {loading ? '—' : value}
            </span>
          </div>
        ))}
      </div>

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