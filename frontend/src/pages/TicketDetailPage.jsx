import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import client from '../api/client'
import { ArrowLeft, Send } from 'lucide-react'

const statusStyle = {
  open: 'border-yellow-800 text-yellow-400',
  assigned: 'border-blue-800 text-blue-400',
  in_progress: 'border-purple-800 text-purple-400',
  resolved: 'border-green-800 text-green-400',
  closed: 'border-zinc-700 text-zinc-500',
}

const priorityStyle = {
  low: 'text-zinc-400',
  medium: 'text-blue-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

const VALID_TRANSITIONS = {
  open: ['assigned', 'in_progress'],
  assigned: ['in_progress', 'open'],
  in_progress: ['resolved'],
  resolved: ['closed', 'in_progress'],
  closed: [],
}

export default function TicketDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [ticket, setTicket] = useState(null)
  const [comments, setComments] = useState([])
  const [loading, setLoading] = useState(true)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const [users, setUsers] = useState([])
  const [assigning, setAssigning] = useState(false)

  const fetchTicket = async () => {
    try {
      const res = await client.get(`/api/v1/tickets/${id}`)
      setTicket(res.data)
    } catch {
      navigate('/tickets')
    }
  }

  const fetchComments = async () => {
    try {
      const res = await client.get(`/api/v1/tickets/${id}/comments`)
      setComments(res.data.items || res.data || [])
    } catch { }
  }
  const fetchUsers = async () => {
    try {
      const res = await client.get('/api/v1/users')
      setUsers(res.data || [])
    } catch { }
  }

  useEffect(() => {
    Promise.all([fetchTicket(), fetchComments(), fetchUsers()]).finally(() => setLoading(false))
  }, [id])

  const changeStatus = async (newStatus) => {
    setStatusLoading(true)
    try {
      await client.patch(`/api/v1/tickets/${id}/status`, { status: newStatus })
      await fetchTicket()
    } catch (err) {
      console.error(err.response?.data)
    } finally {
      setStatusLoading(false)
    }
  }
  const handleAssign = async (assigneeId) => {
    if (!assigneeId) return
    setAssigning(true)
    try {
      await client.patch(`/api/v1/tickets/${id}/assign`, { assignee_id: Number(assigneeId) })
      await fetchTicket()
    } catch (err) {
      console.error(err.response?.data)
    } finally {
      setAssigning(false)
    }
  }

  const submitComment = async () => {
    if (!comment.trim()) return
    setSubmitting(true)
    try {
      await client.post(`/api/v1/tickets/${id}/comments`, { body: comment })
      setComment('')
      await fetchComments()
    } catch (err) {
      console.error(err.response?.data)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="text-zinc-500 text-sm">Loading...</div>
      </Layout>
    )
  }

  if (!ticket) return null

  const nextStatuses = VALID_TRANSITIONS[ticket.status] || []

  return (
    <Layout>
      <div className="max-w-3xl">
        {/* Back */}
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 text-zinc-500 hover:text-white text-sm mb-6 transition-colors"
        >
          <ArrowLeft size={14} />
          Back to tickets
        </button>

        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-xl font-semibold text-white">{ticket.title}</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ${statusStyle[ticket.status]}`}>
              {ticket.status.replace('_', ' ')}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2">
            <span className={`text-xs font-medium ${priorityStyle[ticket.priority]}`}>
              {ticket.priority} priority
            </span>
            <span className="text-xs text-zinc-500">
              Created by {ticket.created_by?.full_name || ticket.created_by?.email}
            </span>
            {ticket.assigned_to && (
              <span className="text-xs text-zinc-500">
                Assigned to {ticket.assigned_to?.full_name || ticket.assigned_to?.email}
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
          <p className="text-xs text-zinc-500 mb-2">Description</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{ticket.description}</p>
        </div>
        {/* Assign */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
        <p className="text-xs text-zinc-500 mb-3">Assign Ticket</p>
        <select
        value={ticket.assigned_to?.id || ''}
        onChange={e => handleAssign(e.target.value)}
        disabled={assigning}
        className="bg-zinc-950 border border-zinc-800 text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-zinc-600 disabled:opacity-50"
        >
          <option value="" disabled>Select an assignee</option>
          {users.map(u => (
            <option key={u.id} value={u.id}>
              {u.full_name} ({u.role})
              </option>
            ))}
            </select>
            </div>
        {/* AI Classification */}
        {ticket.ai_category && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-2">AI Classification</p>
            <div className="flex items-center gap-3">
              <span className="text-sm text-white">{ticket.ai_category}</span>
              {ticket.ai_priority && (
                <span className={`text-xs font-medium ${priorityStyle[ticket.ai_priority]}`}>
                  Suggested: {ticket.ai_priority}
                </span>
              )}
            </div>
            {ticket.ai_summary && (
              <p className="text-xs text-zinc-500 mt-2">{ticket.ai_summary}</p>
            )}
          </div>
        )}

        {/* Status transitions */}
        {nextStatuses.length > 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-3">Change Status</p>
            <div className="flex items-center gap-2">
              {nextStatuses.map(s => (
                <button
                  key={s}
                  onClick={() => changeStatus(s)}
                  disabled={statusLoading}
                  className="text-xs px-3 py-1.5 rounded-md border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white transition-colors disabled:opacity-50"
                >
                  {s.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Comments */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="px-4 py-3 border-b border-zinc-800">
            <span className="text-sm font-medium text-white">Comments</span>
          </div>

          {comments.length === 0 ? (
            <div className="px-4 py-8 text-center text-zinc-600 text-sm">No comments yet</div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {comments.map(c => (
                <div key={c.id} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-zinc-400">
                      {c.author_name || 'Unknown'}
                    </span>
                    <span className="text-xs text-zinc-600">
                      {new Date(c.created_at).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric'
                      })}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-300">{c.body}</p>
                </div>
              ))}
            </div>
          )}

          {/* Add comment */}
          <div className="px-4 py-3 border-t border-zinc-800 flex items-center gap-3">
            <input
              value={comment}
              onChange={e => setComment(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submitComment()}
              placeholder="Add a comment..."
              className="flex-1 bg-zinc-950 border border-zinc-800 text-white text-sm rounded-md px-3 py-2 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
            />
            <button
              onClick={submitComment}
              disabled={submitting || !comment.trim()}
              className="p-2 bg-white text-zinc-950 rounded-md hover:bg-zinc-200 transition-colors disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}