import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res.data?.data !== undefined ? res.data.data : res.data,
  (err) => {
    const msg = err.response?.data?.detail ?? 'An error occurred'
    return Promise.reject(new Error(msg))
  }
)
