import React, { useState } from 'react';
import {
  Video,
  Upload,
  Play,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  X,
  Clock,
  Film
} from 'lucide-react';
import { UserVideo } from '../types';
import { api } from '../services/api';
import { formatISTDateOnly, formatIST } from '../utils/dateUtils';

interface VideosViewProps {
  videos: UserVideo[];
  onVideosChanged: () => void;
}

export const VideosView: React.FC<VideosViewProps> = ({ videos, onVideosChanged }) => {
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState('');
  const [videoDate, setVideoDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [activeVideo, setActiveVideo] = useState<UserVideo | null>(null);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setStatusMsg({ text: 'Please select a video file (MP4, WebM, MOV) to upload.', type: 'error' });
      return;
    }

    setUploading(true);
    setStatusMsg(null);
    try {
      await api.uploadVideo(selectedFile, title, videoDate, description);
      setStatusMsg({ text: `Video "${title}" uploaded successfully to your personal library!`, type: 'success' });
      setTitle('');
      setDescription('');
      setSelectedFile(null);
      onVideosChanged();
    } catch (err: any) {
      setStatusMsg({
        text: err.response?.data?.detail || 'Failed to upload video. Please ensure file is MP4, WebM, or MOV under 100MB.',
        type: 'error'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (videoId: number) => {
    if (!window.confirm('Are you sure you want to delete this video?')) return;
    try {
      await api.deleteVideo(videoId);
      if (activeVideo?.id === videoId) setActiveVideo(null);
      setStatusMsg({ text: 'Video deleted from your library.', type: 'success' });
      onVideosChanged();
    } catch (err: any) {
      setStatusMsg({ text: 'Failed to delete video.', type: 'error' });
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center space-x-3">
            <Video className="w-8 h-8 text-amber-600" />
            <span>Personal Health & Mobility Video Library</span>
          </h1>
          <p className="text-slate-600 text-base mt-1">
            Securely record and store exercise, physical therapy, gait, and mobility recordings with in-browser playback.
          </p>
        </div>
      </div>

      {statusMsg && (
        <div
          className={`p-4 rounded-2xl text-base font-semibold flex items-center space-x-2 border-2 ${
            statusMsg.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-red-50 border-red-300 text-red-900'
          }`}
        >
          {statusMsg.type === 'success' ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
          )}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Video Upload Form */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-6">
        <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2 border-b border-slate-200 pb-3">
          <Upload className="w-5 h-5 text-amber-600" />
          <span>Upload Personal Video</span>
        </h2>

        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Video Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Morning Knee Mobility Exercise"
                className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Recording Date *</label>
              <input
                type="date"
                required
                value={videoDate}
                onChange={(e) => setVideoDate(e.target.value)}
                className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Optional Description / Notes</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Performed 10 repetitions without discomfort"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">
              Select Video File (MP4, WebM, MOV • max 100MB) *
            </label>
            <input
              type="file"
              accept=".mp4,.webm,.mov"
              required
              onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
              className="w-full p-2.5 bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl text-sm font-medium cursor-pointer"
            />
          </div>

          <button
            type="submit"
            disabled={uploading}
            className="bg-amber-600 hover:bg-amber-700 text-white font-black text-lg px-8 py-3.5 rounded-2xl shadow-md transition flex items-center space-x-2 min-h-[48px]"
          >
            <Upload className="w-5 h-5" />
            <span>{uploading ? 'Uploading Video...' : 'Upload Video to Library'}</span>
          </button>
        </form>
      </div>

      {/* Video Gallery */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-6">
        <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2 border-b border-slate-200 pb-3">
          <Film className="w-5 h-5 text-amber-600" />
          <span>My Uploaded Videos ({videos.length})</span>
        </h2>

        {videos.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200 space-y-2">
            <p className="text-base font-bold text-slate-700">No videos in your library yet.</p>
            <p className="text-sm text-slate-500">
              Upload exercise, rehabilitation, or movement recordings above to view them anytime.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {videos.map((vid) => (
              <div
                key={vid.id}
                className="bg-slate-50 rounded-2xl border-2 border-slate-200 p-4 space-y-3 flex flex-col justify-between hover:border-amber-300 transition shadow-sm"
              >
                <div className="space-y-2">
                  {/* Thumbnail / Player preview placeholder */}
                  <div
                    onClick={() => setActiveVideo(vid)}
                    className="w-full h-36 bg-slate-900 rounded-xl flex items-center justify-center cursor-pointer group relative overflow-hidden"
                  >
                    <div className="w-12 h-12 bg-amber-500/90 rounded-full flex items-center justify-center text-white shadow-lg group-hover:scale-110 transition">
                      <Play className="w-6 h-6 fill-white ml-0.5" />
                    </div>
                    <span className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] font-bold px-2 py-0.5 rounded-md uppercase">
                      {vid.file_type}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-bold text-base text-slate-900 leading-snug line-clamp-1">{vid.title}</h3>
                    <p className="text-xs text-slate-500 mt-0.5 flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatISTDateOnly(vid.video_date)} • Uploaded: {formatIST(vid.created_at)} • {(vid.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                    </p>
                  </div>

                  {vid.description && (
                    <p className="text-xs text-slate-600 italic line-clamp-2">{vid.description}</p>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                  <button
                    onClick={() => setActiveVideo(vid)}
                    className="text-xs font-bold text-amber-700 hover:underline flex items-center space-x-1"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Watch Video</span>
                  </button>

                  <button
                    onClick={() => handleDelete(vid.id)}
                    className="text-red-600 hover:text-red-800 p-1.5 rounded-lg hover:bg-red-50 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MODAL: VIDEO PLAYER */}
      {activeVideo && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 text-white rounded-3xl max-w-3xl w-full p-6 shadow-2xl relative space-y-4">
            <button
              onClick={() => setActiveVideo(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-2"
            >
              <X className="w-6 h-6" />
            </button>

            <div>
              <h3 className="text-2xl font-black">{activeVideo.title}</h3>
              <p className="text-xs text-slate-400">Recorded on {formatISTDateOnly(activeVideo.video_date)} • Uploaded {formatIST(activeVideo.created_at)}</p>
            </div>

            <div className="w-full bg-black rounded-2xl overflow-hidden aspect-video flex items-center justify-center">
              <video
                src={activeVideo.stream_url}
                controls
                autoPlay
                className="w-full h-full object-contain"
              >
                Your browser does not support the video tag.
              </video>
            </div>

            {activeVideo.description && (
              <p className="text-sm text-slate-300 italic">{activeVideo.description}</p>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveVideo(null)}
                className="bg-slate-800 hover:bg-slate-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm"
              >
                Close Player
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
