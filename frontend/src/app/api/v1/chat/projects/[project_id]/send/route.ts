import { NextRequest } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ project_id: string }> }
) {
  const { project_id } = await params
  const body = await request.json()

  const backendResponse = await fetch(
    `${BACKEND_URL}/api/v1/chat/projects/${project_id}/send`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Disable compression so SSE chunks aren't buffered by gzip
        'Accept-Encoding': 'identity',
      },
      body: JSON.stringify(body),
    }
  )

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
      'Content-Encoding': 'identity',
    },
  })
}
