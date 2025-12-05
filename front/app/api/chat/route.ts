import { NextResponse } from "next/server"
import Anthropic from "@anthropic-ai/sdk"

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY || "",
})

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { prompt, context } = body

    console.log("Prompt:", prompt)
    console.log("Context length:", context?.length)
    console.log("Context preview:", context?.substring(0, 500) + "...")

    if (!prompt || !context) {
      return NextResponse.json({ error: "Missing prompt or context" }, { status: 400 })
    }

    console.log("Making Anthropic API call...")
    const message = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 16384,
      system: `You are a helpful and intelligent meeting assistant embedded in a productivity app. Your goal is to help users understand, summarize, and get insights from their meeting transcripts.

You have access to the full transcript of each meeting, including speaker labels, timestamps, and optionally topics. Be concise, clear, and professional.

If asked a specific question, base your answer only on the content of the transcript provided. Do not make assumptions or add external context.

Use bullet points or headings where appropriate to make your responses easier to scan.

You must support multiple languages, including Kazakh and Russian mostly. Use the same language as the input unless specified otherwise.

If transcript data is missing or ambiguous, politely inform the user.

Never include disclaimers about being an AI, and avoid redundant explanations. Just give the user what they need.
Your responses should be in the same language as the input, unless specified otherwise.
You are not allowed to provide any personal opinions or subjective interpretations. Stick to the facts and the content of the transcript.

TRANSCRIPT CONTEXT:
${context}`,
      messages: [
        {
          role: "user",
          content: prompt,
        },
      ],
    })

    console.log("Anthropic API call successful")
    const text = message.content[0].type === "text" ? message.content[0].text : ""

    return NextResponse.json({ text })
  } catch (err) {
    console.error("🔥 AI Chat Error - Full error object:", err)

    // Log specific error properties
    if (err instanceof Error) {
      console.error("Error name:", err.name)
      console.error("Error message:", err.message)
      console.error("Error stack:", err.stack)
    }

    // Log Anthropic-specific error details
    if (err && typeof err === "object") {
      console.error("Error type:", err.constructor?.name)
      console.error("Error status:", (err as any).status)
      console.error("Error code:", (err as any).code)
      console.error("Error response:", (err as any).response)
      console.error("Error headers:", (err as any).headers)
      console.error("Error body:", (err as any).body)

      // If it's an Anthropic API error, log the full response
      if ((err as any).response) {
        console.error("API Response status:", (err as any).response.status)
        console.error("API Response statusText:", (err as any).response.statusText)
        console.error("API Response data:", (err as any).response.data)
      }
    }

    // Log all enumerable properties
    console.error("All error properties:", Object.getOwnPropertyNames(err))
    for (const key in err) {
      console.error(`Error.${key}:`, (err as any)[key])
    }

    return NextResponse.json({ error: "AI processing failed" }, { status: 500 })
  }
}
