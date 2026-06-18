import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { ArrowLeft, Send } from 'lucide-react'

const statusStyle = {
  pending_review: 'border-yellow-800 text-yellow-400',
  accepted: 'border-blue-800 text-blue-400',
  assigned: 'border-indigo-800 text-indigo-400',
  in_progress: 'border-purple-800 text-purple-400',
  resolved: 'border-green-800 text-green-400',
  rejected: 'border-red-800 text-red-400',
  closed: 'border-zinc-700 text-zinc-500',
}

const priorityStyle = {
  low: 'text-zinc-400',
  medium: 'text-blue-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

// Matches backend VALID_TRANSITIONS exactly
const VALID_TRANSITIONS = {
  pending_review: [],
  accepted: [],
  assigned: ['in_progress'],
  in_progress: ['resolved'],
  resolved: ['closed'],
  rejected: [],
  closed: [],
}

export default function TicketDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [ticket, setTicket] = useState(null)
  const [comments, setComments] = useState([])
  const [loading, setLoading] = useState(true)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const [assignLoading, setAssignLoading] = useState(false)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [deptMembers, setDeptMembers] = useState([])
  const [rejectionReason, setRejectionReason] = useState('')
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'
  const isManager = user?.role === 'manager'
  const isMember = user?.role === 'member'

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
    } catch {}
  }

  const fetchDeptMembers = async (deptId) => {
    try {
      const res = await client.get(`/api/v1/users?department_id=${deptId}&role=member`)
      setDeptMembers(res.data || [])
    } catch {}
  }

  useEffect(() => {
    Promise.all([fetchTicket(), fetchComments()]).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (ticket && (isManager || isAdmin)) {
      fetchDeptMembers(ticket.target_department?.id)
    }
  }, [ticket])

  const changeStatus = async (newStatus) => {
    setStatusLoading(true)
    setError('')
    try {
      await client.patch(`/api/v1/tickets/${id}/status`, { status: newStatus })
      await fetchTicket()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update status')
    } finally {
      setStatusLoading(false)
    }
  }

  const handleAssign = async (assigneeId) => {
    if (!assigneeId) return
    setAssignLoading(true)
    setError('')
    try {
      await client.patch(`/api/v1/tickets/${id}/assign`, { assignee_id: Number(assigneeId) })
      await fetchTicket()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to assign ticket')
    } finally {
      setAssignLoading(false)
    }
  }

  const handleReview = async (action) => {
    if (action === 'rejected' && !rejectionReason.trim()) {
      setError('Rejection reason is required.')
      return
    }
    setReviewLoading(true)
    setError('')
    try {
      await client.patch(`/api/v1/tickets/${id}/review`, {
        action,
        rejection_reason: action === 'rejected' ? rejectionReason : null,
      })
      setShowRejectInput(false)
      setRejectionReason('')
      await fetchTicket()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to review ticket')
    } finally {
      setReviewLoading(false)
    }
  }

  const submitComment = async () => {
    if (!comment.trim()) return
    setSubmitting(true)
    try {
      await client.post(`/api/v1/tickets/${id}/comments`, { body: comment })
      setComment('')
      await fetchComments()
    } catch {}
    finally { setSubmitting(false) }
  }

  if (loading) return <Layout><div className="text-zinc-500 text-sm">Loading...</div></Layout>
  if (!ticket) return null

  const nextStatuses = VALID_TRANSITIONS[ticket.status] || []
  const canReview = (isManager || isAdmin) && ticket.status === 'pending_review'
  const canAssign = (isManager || isAdmin) && ticket.status === 'accepted'
  const canChangeStatus = (isAdmin || (isMember && ticket.assigned_to?.id === user?.id)) && nextStatuses.length > 0

  return (
    <Layout>
      <div className="max-w-3xl">
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
            <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ${statusStyle[ticket.status] || 'border-zinc-700 text-zinc-400'}`}>
              {ticket.status.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 flex-wrap">
            <span className={`text-xs font-medium ${priorityStyle[ticket.priority]}`}>
              {ticket.priority} priority
            </span>
            <span className="text-xs text-zinc-500">
              Dept: {ticket.target_department?.name}
            </span>
            <span className="text-xs text-zinc-500">
              Created by {ticket.created_by?.full_name}
            </span>
            {ticket.assigned_to && (
              <span className="text-xs text-zinc-500">
                Assigned to {ticket.assigned_to?.full_name}
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-4 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {/* Description */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
          <p className="text-xs text-zinc-500 mb-2">Description</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{ticket.description}</p>
        </div>

        {/* Manager: Review (approve/reject) */}
        {canReview && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-3">Review Ticket</p>
            {!showRejectInput ? (
              <div className="flex gap-2">
                <button
                  onClick={() => handleReview('accepted')}
                  disabled={reviewLoading}
                  className="px-4 py-1.5 text-xs font-medium bg-green-500/10 border border-green-500/30 text-green-400 rounded-md hover:bg-green-500/20 transition-colors disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  onClick={() => setShowRejectInput(true)}
                  disabled={reviewLoading}
                  className="px-4 py-1.5 text-xs font-medium bg-red-500/10 border border-red-500/30 text-red-400 rounded-md hover:bg-red-500/20 transition-colors disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <textarea
                  value={rejectionReason}
                  onChange={e => setRejectionReason(e.target.value)}
                  placeholder="Reason for rejection..."
                  rows={2}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-600 resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReview('rejected')}
                    disabled={reviewLoading}
                    className="px-4 py-1.5 text-xs font-medium bg-red-500/10 border border-red-500/30 text-red-400 rounded-md hover:bg-red-500/20 disabled:opacity-50"
                  >
                    Confirm Reject
                  </button>
                  <button
                    onClick={() => { setShowRejectInput(false); setRejectionReason('') }}
                    className="px-4 py-1.5 text-xs text-zinc-400 hover:text-white"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Rejection reason display */}
        {ticket.status === 'rejected' && ticket.rejection_reason && (
          <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 mb-4">
            <p className="text-xs text-red-400 mb-1">Rejection Reason</p>
            <p className="text-sm text-zinc-300">{ticket.rejection_reason}</p>
          </div>
        )}

        {/* Manager: Assign */}
        {canAssign && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-3">Assign to Member</p>
            <select
              defaultValue=""
              onChange={e => handleAssign(e.target.value)}
              disabled={assignLoading}
              className="bg-zinc-950 border border-zinc-800 text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-zinc-600 disabled:opacity-50"
            >
              <option value="" disabled>Select a member</option>
              {deptMembers.map(u => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </select>
          </div>
        )}

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

        {/* Member: Status transitions */}
        {canChangeStatus && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-3">Update Status</p>
            <div className="flex items-center gap-2">
              {nextStatuses.map(s => (
                <button
                  key={s}
                  onClick={() => changeStatus(s)}
                  disabled={statusLoading}
                  className="text-xs px-3 py-1.5 rounded-md border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white transition-colors disabled:opacity-50"
                >
                  {s.replace(/_/g, ' ')}
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
                    <span className="text-xs font-medium text-zinc-400">{c.author_name || 'Unknown'}</span>
                    <span className="text-xs text-zinc-600">
                      {new Date(c.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-300">{c.body}</p>
                </div>
              ))}
            </div>
          )}
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