/**
 * ResourceTimeline - Displays the timeline header with date labels.
 */

import {
  format,
  eachDayOfInterval,
  startOfWeek,
  startOfMonth,
  isSameDay,
  isWeekend,
} from "date-fns";
import type { GanttResourceViewConfig } from "@/types/ganttResource";

interface ResourceTimelineProps {
  config: GanttResourceViewConfig;
  width: number;
}

export function ResourceTimeline({ config, width }: ResourceTimelineProps) {
  const days = eachDayOfInterval({
    start: config.startDate,
    end: config.endDate,
  });
  const dayWidth =
    config.scale === "day" ? 40 : config.scale === "week" ? 20 : 8;

  // Generate month/week headers
  const monthHeaders: { label: string; startIndex: number; span: number }[] =
    [];
  let currentMonth: string | null = null;
  let currentMonthStart = 0;

  days.forEach((day, index) => {
    const monthKey = format(day, "MMM yyyy");
    if (monthKey !== currentMonth) {
      if (currentMonth !== null) {
        monthHeaders.push({
          label: currentMonth,
          startIndex: currentMonthStart,
          span: index - currentMonthStart,
        });
      }
      currentMonth = monthKey;
      currentMonthStart = index;
    }
  });
  // Push the last month
  if (currentMonth !== null) {
    monthHeaders.push({
      label: currentMonth,
      startIndex: currentMonthStart,
      span: days.length - currentMonthStart,
    });
  }

  // Determine which days to show labels for
  const shouldShowLabel = (day: Date): boolean => {
    if (config.scale === "day") {
      return true;
    }
    if (config.scale === "week") {
      return isSameDay(day, startOfWeek(day, { weekStartsOn: 1 }));
    }
    // Month scale - show first of month
    return isSameDay(day, startOfMonth(day));
  };

  return (
    <div
      className="resource-timeline"
      style={{ width, height: config.headerHeight }}
      data-testid="resource-timeline"
    >
      {/* Month row */}
      <div className="timeline-months">
        {monthHeaders.map((header, idx) => (
          <div
            key={idx}
            className="timeline-month"
            style={{
              left: header.startIndex * dayWidth,
              width: header.span * dayWidth,
            }}
          >
            {header.label}
          </div>
        ))}
      </div>

      {/* Day row */}
      <div className="timeline-days">
        {days.map((day, index) => (
          <div
            key={index}
            className={`timeline-day ${isWeekend(day) ? "weekend" : ""}`}
            style={{
              left: index * dayWidth,
              width: dayWidth,
            }}
          >
            {shouldShowLabel(day) && (
              <span className="timeline-day-label">
                {config.scale === "day"
                  ? format(day, "d")
                  : config.scale === "week"
                  ? format(day, "d")
                  : format(day, "d")}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
