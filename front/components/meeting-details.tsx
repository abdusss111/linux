"use client"

import { MeetingHeader } from "./meeting-header"
import type { Meeting } from "@/lib/types"

interface MeetingDetailsProps {
  meeting: Meeting
}

export function MeetingDetails({ meeting }: MeetingDetailsProps) {
  return (
    <div className="space-y-6">
      <MeetingHeader meeting={meeting} />
    </div>
  )
}
