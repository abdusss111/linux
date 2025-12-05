export interface User {
  id: string
  name: string
  email: string
  image: string | null
}

export interface MeetingSegment {
  id: number
  session_id: string
  google_meet_user_id: string
  speaker_username: string
  timestamp: string
  text: string
  version: number
  message_id: string
  created_at: string
}

export interface Meeting {
  unique_session_id: string
  meeting_id: string
  user_id: string
  title: string
  segments: MeetingSegment[]
  created_at: string
  speakers: string[]
}

export interface ProcessedSegment extends MeetingSegment {
  groupedMessages: string[]
  isFirstInGroup: boolean
  speakerColor: string
}

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  loginWithGoogle: () => void
  logout: () => void
}
