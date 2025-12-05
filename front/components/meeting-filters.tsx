// "use client"

// import { useState } from "react"
// import { Button } from "@/components/ui/button"
// import { CalendarIcon } from "lucide-react"
// import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
// import { Calendar } from "@/components/ui/calendar"
// import { format } from "date-fns"
// import { ru } from "date-fns/locale"

// export default function MeetingFilters() {
//   const [date, setDate] = useState<Date | undefined>(undefined)

//   return (
//     <div className="flex items-center gap-2">
//       <Popover>
//         <PopoverTrigger asChild>
//           <Button variant="outline" size="sm" className="h-9 gap-1">
//             <CalendarIcon className="h-4 w-4" />
//             {date ? format(date, "PPP", { locale: ru }) : "Выбрать дату"}
//           </Button>
//         </PopoverTrigger>
//         <PopoverContent className="w-auto p-0" align="end">
//           <Calendar mode="single" selected={date} onSelect={setDate} initialFocus locale={ru} />
//         </PopoverContent>
//       </Popover>

//       {date && (
//         <Button variant="ghost" size="sm" onClick={() => setDate(undefined)}>
//           Очистить фильтры
//         </Button>
//       )}
//     </div>
//   )
// }
