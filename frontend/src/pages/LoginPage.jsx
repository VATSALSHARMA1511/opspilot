import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState([])
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', department_id: ''
  })

  useEffect(() => {
    client.get('/api/v1/departments').then(res => setDepartments(res.data || [])).catch(() => {})
  }, [])

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async () => {
    setError('')
    if (isRegister && !form.department_id) {
      setError('Please select a department.')
      return
    }
    setLoading(true)
    try {
      if (isRegister) {
        const res = await client.post('/api/v1/auth/register', {
          full_name: form.full_name,
          email: form.email,
          password: form.password,
          department_id: Number(form.department_id),
        })
        login(res.data.access_token, res.data.refresh_token, res.data.user)
      } else {
        const res = await client.post('/api/v1/auth/login', {
          email: form.email, password: form.password
        })
        login(res.data.access_token, res.data.refresh_token, res.data.user)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-white tracking-tight">OpsPilot</h1>
          <p className="text-zinc-500 text-sm mt-1">
            {isRegister ? 'Create your account' : 'Sign in to your account'}
          </p>
        </div>

        <div className="space-y-3">
          {isRegister && (
            <input
              name="full_name"
              placeholder="Full name"
              onChange={handle}
              className="w-full bg-zinc-900 border border-zinc-800 text-white text-sm rounded-md px-3 py-2.5 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
            />
          )}
          <input
            name="email"
            type="email"
            placeholder="Email"
            onChange={handle}
            className="w-full bg-zinc-900 border border-zinc-800 text-white text-sm rounded-md px-3 py-2.5 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
          />
          <input
            name="password"
            type="password"
            placeholder="Password"
            onChange={handle}
            className="w-full bg-zinc-900 border border-zinc-800 text-white text-sm rounded-md px-3 py-2.5 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
          />
          {isRegister && (
            <select
              name="department_id"
              value={form.department_id}
              onChange={handle}
              className="w-full bg-zinc-900 border border-zinc-800 text-white text-sm rounded-md px-3 py-2.5 focus:outline-none focus:border-zinc-600"
            >
              <option value="" disabled>Select your department</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          )}
        </div>

        {error && <p className="text-red-400 text-xs mt-3">{error}</p>}

        <button
          onClick={submit}
          disabled={loading}
          className="mt-4 w-full bg-white text-zinc-950 text-sm font-medium rounded-md py-2.5 hover:bg-zinc-200 transition-colors disabled:opacity-50"
        >
          {loading ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
        </button>

        <p className="text-zinc-600 text-xs mt-4 text-center">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsRegister(!isRegister); setError('') }}
            className="text-zinc-400 hover:text-white transition-colors"
          >
            {isRegister ? 'Sign in' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  )
}