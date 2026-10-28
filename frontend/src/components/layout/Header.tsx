import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Search, Bell, LogOut, Shield, Check, ExternalLink, AlertTriangle, CheckCircle, XCircle, Info, ChevronDown, ChevronUp, FileText, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../services/api";
import type { NotificationItem } from "../../types";

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [expandedNotifId, setExpandedNotifId] = useState<number | null>(null);
  const [selectedNotifForModal, setSelectedNotifForModal] = useState<NotificationItem | null>(null);

  useEffect(() => {
    loadNotifications();
  }, [location.pathname]);

  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(data);
    } catch {
      // ignore
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/applications?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {}
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {}
  };

  const getActionBadge = (notif: NotificationItem) => {
    const action = notif.action_type || notif.notification_type;
    switch (action) {
      case "APPROVE":
      case "SUCCESS":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle className="w-2.5 h-2.5" /> Approved
          </span>
        );
      case "REJECT":
      case "ERROR":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
            <XCircle className="w-2.5 h-2.5" /> Rejected
          </span>
        );
      case "REQUEST_CORRECTION":
      case "CLARIFICATION_REQUESTED":
      case "RETURN":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-2.5 h-2.5" /> Correction Required
          </span>
        );
      case "REQUEST_DOCUMENTS":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
            <FileText className="w-2.5 h-2.5" /> Docs Required
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
            <Info className="w-2.5 h-2.5" /> Under Review
          </span>
        );
      case "CORRECTION_SUBMITTED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
            <CheckCircle className="w-2.5 h-2.5" /> Correction Submitted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-700">
            Notice
          </span>
        );
    }
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-[#DCE4ED] px-6 flex items-center justify-between shadow-xs sticky top-0 z-30">
        {/* Search Input */}
        <form onSubmit={handleSearch} className="flex-1 max-w-md relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Application Ref, Institution, AICTE ID, or Document..."
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-[#F4F7FB] border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8] focus:bg-white text-slate-800"
          />
        </form>

        {/* Right Controls */}
        <div className="flex items-center gap-4">
          {/* Role Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Shield className="w-3.5 h-3.5 text-[#1677C8]" />
            <span>{user?.role?.replace(/_/g, " ")}</span>
          </div>

          {/* Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg relative transition-colors cursor-pointer"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-rose-600 text-white rounded-full text-[10px] font-bold flex items-center justify-center animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 sm:w-[420px] bg-white rounded-xl shadow-2xl border border-[#DCE4ED] z-50 overflow-hidden">
                <div className="p-3 bg-slate-50 border-b border-[#DCE4ED] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-800">
                      Regulatory Scrutiny Notifications
                    </span>
                    {unreadCount > 0 && (
                      <span className="px-1.5 py-0.5 bg-rose-100 text-rose-700 font-bold text-[10px] rounded-full">
                        {unreadCount} unread
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="text-[11px] text-[#1677C8] hover:underline font-semibold"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
                  {notifications.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                      No regulatory notifications received.
                    </div>
                  ) : (
                    notifications.map((notif) => {
                      const isExpanded = expandedNotifId === notif.id;
                      return (
                        <div
                          key={notif.id}
                          className={`p-3 text-xs transition-colors ${
                            notif.is_read ? "bg-white" : "bg-blue-50/40 font-medium"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                {getActionBadge(notif)}
                                <span className="text-[10px] text-slate-400">
                                  {new Date(notif.created_at).toLocaleString([], {
                                    month: "short",
                                    day: "numeric",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </span>
                              </div>
                              <div className="font-semibold text-slate-900 leading-tight">
                                {notif.title}
                              </div>
                            </div>

                            <div className="flex items-center gap-1 shrink-0">
                              {!notif.is_read && (
                                <button
                                  onClick={() => handleMarkRead(notif.id)}
                                  className="p-1 text-slate-400 hover:text-emerald-600 rounded hover:bg-emerald-50 transition-colors"
                                  title="Mark read"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </div>

                          <p className="text-slate-600 mt-1.5 leading-relaxed text-[11px]">
                            {notif.message}
                          </p>

                          {/* Details preview or expand */}
                          {notif.details && (
                            <div className="mt-2">
                              {isExpanded ? (
                                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md text-[11px] text-slate-700 whitespace-pre-wrap font-sans">
                                  {notif.details}
                                  <button
                                    onClick={() => setExpandedNotifId(null)}
                                    className="mt-1 text-[10px] text-slate-500 hover:text-slate-700 flex items-center gap-0.5"
                                  >
                                    <ChevronUp className="w-3 h-3" /> Collapse
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => setExpandedNotifId(notif.id)}
                                  className="text-[10px] text-[#1677C8] hover:underline flex items-center gap-0.5 font-semibold"
                                >
                                  <ChevronDown className="w-3 h-3" /> View Officer Details / Justification
                                </button>
                              )}
                            </div>
                          )}

                          <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100">
                            {notif.details && (
                              <button
                                onClick={() => {
                                  setSelectedNotifForModal(notif);
                                  setShowNotifications(false);
                                }}
                                className="text-[10px] text-slate-600 hover:text-[#1677C8] font-medium"
                              >
                                Full Notice Memo
                              </button>
                            )}

                            {notif.link ? (
                              <button
                                onClick={() => {
                                  setShowNotifications(false);
                                  navigate(notif.link!);
                                }}
                                className="ml-auto text-[#1677C8] text-[11px] font-semibold flex items-center gap-1 hover:underline"
                              >
                                <span>Go to Application</span>
                                <ExternalLink className="w-3 h-3" />
                              </button>
                            ) : notif.application_id ? (
                              <button
                                onClick={() => {
                                  setShowNotifications(false);
                                  navigate(`/applications/${notif.application_id}`);
                                }}
                                className="ml-auto text-[#1677C8] text-[11px] font-semibold flex items-center gap-1 hover:underline"
                              >
                                <span>Go to Application</span>
                                <ExternalLink className="w-3 h-3" />
                              </button>
                            ) : null}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User Profile & Logout */}
          <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
            <div className="text-right hidden md:block">
              <div className="text-xs font-bold text-slate-900 leading-tight">
                {user?.full_name}
              </div>
              <div className="text-[11px] text-slate-500 truncate max-w-[150px]">
                {user?.email}
              </div>
            </div>
            <button
              onClick={logout}
              className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
              title="Secure Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Full Notification Memo Modal */}
      {selectedNotifForModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                <h3 className="font-bold text-sm">Official Regulatory Notice</h3>
              </div>
              <button
                onClick={() => setSelectedNotifForModal(null)}
                className="text-slate-400 hover:text-white p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <div className="font-bold text-slate-900 text-sm">
                    {selectedNotifForModal.title}
                  </div>
                  <div className="text-slate-500 text-[11px] mt-0.5">
                    {new Date(selectedNotifForModal.created_at).toLocaleString()}
                  </div>
                </div>
                {getActionBadge(selectedNotifForModal)}
              </div>

              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                  Summary Notice
                </label>
                <p className="text-slate-800 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {selectedNotifForModal.message}
                </p>
              </div>

              {selectedNotifForModal.details && (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Official Officer Findings & Instructions
                  </label>
                  <div className="bg-blue-50/50 p-3 rounded-lg border border-blue-200 text-slate-800 leading-relaxed font-sans whitespace-pre-wrap">
                    {selectedNotifForModal.details}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setSelectedNotifForModal(null)}
                className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 font-semibold rounded-lg hover:bg-slate-100"
              >
                Close
              </button>
              {(selectedNotifForModal.link || selectedNotifForModal.application_id) && (
                <button
                  onClick={() => {
                    const target = selectedNotifForModal.link || `/applications/${selectedNotifForModal.application_id}`;
                    setSelectedNotifForModal(null);
                    navigate(target);
                  }}
                  className="px-4 py-1.5 bg-[#1677C8] hover:bg-[#125ea0] text-white font-semibold rounded-lg flex items-center gap-1.5 shadow-xs"
                >
                  <span>Open Application Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

