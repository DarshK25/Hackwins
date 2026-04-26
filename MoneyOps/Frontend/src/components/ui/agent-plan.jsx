import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  Circle,
  CircleAlert,
  CircleDotDashed,
  CircleX,
} from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";

function StatusIcon({ status, size = "h-4 w-4" }) {
  if (status === "completed") return <CheckCircle2 className={`${size} text-[#4CBB17]`} />;
  if (status === "in-progress") return <CircleDotDashed className={`${size} text-[#60A5FA]`} />;
  if (status === "need-help") return <CircleAlert className={`${size} text-[#FFB300]`} />;
  if (status === "failed") return <CircleX className={`${size} text-[#CD1C18]`} />;
  return <Circle className={`${size} text-[#777777]`} />;
}

function statusClasses(status) {
  if (status === "completed") return "border-[#4CBB1740] bg-[#4CBB1715] text-[#7EE35A]";
  if (status === "in-progress") return "border-[#60A5FA40] bg-[#60A5FA15] text-[#93C5FD]";
  if (status === "need-help") return "border-[#FFB30040] bg-[#FFB30015] text-[#FFD166]";
  if (status === "failed") return "border-[#CD1C1840] bg-[#CD1C1815] text-[#FF7B78]";
  return "border-[#2A2A2A] bg-[#171717] text-[#A0A0A0]";
}

function priorityClasses(priority) {
  if (priority === "high") return "text-[#FFB300]";
  if (priority === "medium") return "text-[#A0A0A0]";
  return "text-[#7D8A7A]";
}

export function AgentPlan({ title = "Execution Plan", subtitle, tasks = [] }) {
  const [expandedTasks, setExpandedTasks] = useState(tasks.slice(0, 1).map((task) => task.id));
  const [expandedSubtasks, setExpandedSubtasks] = useState({});

  const prefersReducedMotion = useMemo(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  const taskVariants = {
    hidden: { opacity: 0, y: prefersReducedMotion ? 0 : 8 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: prefersReducedMotion ? 0.14 : 0.22 },
    },
  };

  const listVariants = {
    hidden: { opacity: 0, height: 0 },
    visible: {
      opacity: 1,
      height: "auto",
      transition: { duration: prefersReducedMotion ? 0.16 : 0.24, staggerChildren: prefersReducedMotion ? 0 : 0.05 },
    },
    exit: { opacity: 0, height: 0, transition: { duration: 0.18 } },
  };

  const subtaskVariants = {
    hidden: { opacity: 0, x: prefersReducedMotion ? 0 : -10 },
    visible: { opacity: 1, x: 0, transition: { duration: prefersReducedMotion ? 0.14 : 0.2 } },
    exit: { opacity: 0, x: prefersReducedMotion ? 0 : -10, transition: { duration: 0.16 } },
  };

  function toggleTask(taskId) {
    setExpandedTasks((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId]
    );
  }

  function toggleSubtask(taskId, subtaskId) {
    const key = `${taskId}:${subtaskId}`;
    setExpandedSubtasks((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <div className="overflow-hidden rounded-[20px] border border-[#2A2A2A] bg-[#121212] shadow-[0_0_0_1px_rgba(255,255,255,0.01)]">
      <div className="border-b border-[#2A2A2A] bg-[radial-gradient(circle_at_top_left,rgba(76,187,23,0.12),transparent_38%),linear-gradient(180deg,#151515_0%,#101010_100%)] px-5 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#4CBB17]">Market Agent</p>
        <h3 className="mt-2 text-xl font-semibold text-white">{title}</h3>
        {subtitle ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[#A0A0A0]">{subtitle}</p> : null}
      </div>

      <LayoutGroup>
        <div className="px-3 py-3">
          <ul className="space-y-2">
            {tasks.map((task) => {
              const expanded = expandedTasks.includes(task.id);

              return (
                <motion.li key={task.id} initial="hidden" animate="visible" variants={taskVariants} layout>
                  <div className="overflow-hidden rounded-2xl border border-[#202020] bg-[#0E0E0E]">
                    <button
                      type="button"
                      onClick={() => toggleTask(task.id)}
                      className="flex w-full items-start gap-3 px-4 py-4 text-left transition-colors hover:bg-[#131313]"
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        <StatusIcon status={task.status} />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="text-sm font-semibold text-white">{task.title}</h4>
                              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClasses(task.status)}`}>
                                {task.status.replace("-", " ")}
                              </span>
                              <span className={`text-[11px] font-medium uppercase tracking-wide ${priorityClasses(task.priority)}`}>
                                {task.priority} priority
                              </span>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-[#A0A0A0]">{task.description}</p>
                            {task.dependencies?.length ? (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {task.dependencies.map((dependency) => (
                                  <span
                                    key={dependency}
                                    className="rounded-full border border-[#2A2A2A] bg-[#151515] px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-[#A0A0A0]"
                                  >
                                    Depends on {dependency}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                          </div>

                          <ChevronDown
                            className={`mt-0.5 h-4 w-4 flex-shrink-0 text-[#777777] transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        </div>
                      </div>
                    </button>

                    <AnimatePresence initial={false}>
                      {expanded && task.subtasks?.length ? (
                        <motion.div
                          variants={listVariants}
                          initial="hidden"
                          animate="visible"
                          exit="exit"
                          className="border-t border-[#1D1D1D]"
                          layout
                        >
                          <ul className="space-y-2 px-4 py-4">
                            {task.subtasks.map((subtask) => {
                              const subtaskKey = `${task.id}:${subtask.id}`;
                              const subtaskExpanded = expandedSubtasks[subtaskKey];

                              return (
                                <motion.li
                                  key={subtask.id}
                                  variants={subtaskVariants}
                                  initial="hidden"
                                  animate="visible"
                                  exit="exit"
                                  layout
                                  className="rounded-2xl border border-[#1D1D1D] bg-[#111111]"
                                >
                                  <button
                                    type="button"
                                    onClick={() => toggleSubtask(task.id, subtask.id)}
                                    className="flex w-full items-start gap-3 px-4 py-3 text-left"
                                  >
                                    <div className="mt-0.5 flex-shrink-0">
                                      <StatusIcon status={subtask.status} size="h-3.5 w-3.5" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                      <div className="flex items-start justify-between gap-3">
                                        <div>
                                          <div className="flex flex-wrap items-center gap-2">
                                            <p className="text-sm font-medium text-white">{subtask.title}</p>
                                            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClasses(subtask.status)}`}>
                                              {subtask.status.replace("-", " ")}
                                            </span>
                                          </div>
                                          <p className="mt-1 text-xs uppercase tracking-wide text-[#6E6E6E]">
                                            {subtask.priority} priority
                                          </p>
                                        </div>
                                        <ChevronDown
                                          className={`mt-0.5 h-4 w-4 flex-shrink-0 text-[#666666] transition-transform ${
                                            subtaskExpanded ? "rotate-180" : ""
                                          }`}
                                        />
                                      </div>
                                    </div>
                                  </button>

                                  <AnimatePresence initial={false}>
                                    {subtaskExpanded ? (
                                      <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: prefersReducedMotion ? 0.14 : 0.2 }}
                                        className="overflow-hidden border-t border-[#1D1D1D]"
                                      >
                                        <div className="space-y-3 px-4 py-3">
                                          <p className="text-sm leading-6 text-[#A0A0A0]">{subtask.description}</p>
                                        </div>
                                      </motion.div>
                                    ) : null}
                                  </AnimatePresence>
                                </motion.li>
                              );
                            })}
                          </ul>
                        </motion.div>
                      ) : null}
                    </AnimatePresence>
                  </div>
                </motion.li>
              );
            })}
          </ul>
        </div>
      </LayoutGroup>
    </div>
  );
}

export default AgentPlan;
