"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar, Search, User } from "lucide-react"
import { Input } from "@/components/ui/input"
import type { Meeting } from "@/lib/types"
import Link from "next/link"
import { formatDate } from "@/lib/utils"

// Mock data for development
const mockMeetings: Meeting[] = [
  {
    id: "1",
    title: "Weekly Team Sync",
    date: "2023-05-15T10:00:00Z",
    participants: ["John Doe", "Jane Smith", "Bob Johnson"],
    status: "completed",
  },
  {
    id: "2",
    title: "Product Planning",
    date: "2023-05-18T14:30:00Z",
    participants: ["Jane Smith", "Alice Brown", "Charlie Davis"],
    status: "scheduled",
  },
  {
    id: "3",
    title: "Client Presentation",
    date: "2023-05-20T09:00:00Z",
    participants: ["John Doe", "Bob Johnson", "Eve Wilson"],
    status: "scheduled",
  },
]

interface MeetingsListProps {
  filter?: "all" | "recent" | "upcoming"
}

export default function MeetingsList({ filter = "all" }: MeetingsListProps) {
  const [searchQuery, setSearchQuery] = useState("")

  // In a real app, this would fetch from an API
  const { data: meetings = mockMeetings, isLoading } = useQuery<Meeting[]>({
    queryKey: ["meetings", filter],
    queryFn: async () => {
      // In a real app, fetch from API
      // const response = await fetch(`/api/meetings${filter !== "all" ? `?filter=${filter}` : ""}`)
      // if (!response.ok) throw new Error("Failed to fetch meetings")
      // return response.json()

      // For now, return mock data
      return mockMeetings
    },
  })

  const filteredMeetings = meetings.filter((meeting) => meeting.title.toLowerCase().includes(searchQuery.toLowerCase()))

  if (isLoading) {
    return <div>Loading meetings...</div>
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Meetings</CardTitle>
          <CardDescription>You have {meetings.length} total meetings</CardDescription>
        </div>
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search meetings..."
            className="w-full pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {filteredMeetings.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-muted-foreground">No meetings found</p>
            </div>
          ) : (
            filteredMeetings.map((meeting) => (
              <div
                key={meeting.id}
                className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-lg border p-4"
              >
                <div className="space-y-1">
                  <h3 className="font-medium">{meeting.title}</h3>
                  <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>{formatDate(meeting.date)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <User className="h-4 w-4" />
                      <span>{meeting.participants.length} participants</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <Badge variant={meeting.status === "completed" ? "default" : "secondary"}>{meeting.status}</Badge>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/meetings/${meeting.id}`}>View Details</Link>
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
