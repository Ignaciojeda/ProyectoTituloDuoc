import api from './client'

const memo = new Map()

export function getCached(url) {
  if (!memo.has(url)) {
    memo.set(url, api.get(url).then(r => r.data).catch(e => { memo.delete(url); throw e }))
  }
  return memo.get(url)
}