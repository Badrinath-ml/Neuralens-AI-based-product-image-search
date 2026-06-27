import { useEffect, useRef, useState } from "react";
import type { DetectedObject } from "../types";
import { detectObjects } from "../api/client";

interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (blob: Blob) => void;
  isSearching: boolean;
}

export default function CameraModal({
  isOpen,
  onClose,
  onCapture,
  isSearching,
}: CameraModalProps) {
  const [mode, setMode] = useState<"snapshot" | "stream">("snapshot");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [permissionError, setPermissionError] = useState<string>("");
  const [detectedObjects, setDetectedObjects] = useState<DetectedObject[]>([]);
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [streamError, setStreamError] = useState<string>("");

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Primary camera init: request access first (no device ID), then enumerate for switcher
  useEffect(() => {
    if (!isOpen) return;

    setPermissionError("");
    setStreamError("");

    let mounted = true;

    // Step 1: get camera permission with a generic request — this must happen BEFORE
    // enumerateDevices() can return real device IDs and labels in the browser
    navigator.mediaDevices
      .getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      .then((stream) => {
        if (!mounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        // Step 2: now enumerate real device IDs (only available after permission granted)
        return navigator.mediaDevices.enumerateDevices();
      })
      .then((deviceInfos) => {
        if (!mounted || !deviceInfos) return;
        const videoDevices = deviceInfos.filter((d) => d.kind === "videoinput");
        setDevices(videoDevices);
        if (videoDevices.length > 0) {
          // Find the currently active track's device to mark it as selected
          const activeTrack = streamRef.current?.getVideoTracks()[0];
          const activeSettings = activeTrack?.getSettings();
          const activeId = activeSettings?.deviceId;
          setSelectedDeviceId(activeId || videoDevices[0].deviceId);
        }
      })
      .catch((err) => {
        if (!mounted) return;
        console.error("Camera access failed:", err);
        const isPermDenied = err.name === "NotAllowedError" || err.name === "PermissionDeniedError";
        setPermissionError(
          isPermDenied
            ? "Camera permission denied. Please allow camera access in your browser settings and try again."
            : "Could not access camera. Make sure no other app is using it and try again."
        );
      });

    return () => {
      mounted = false;
      // Stop the stream when modal closes
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setDevices([]);
      setSelectedDeviceId("");
      setDetectedObjects([]);
    };
  }, [isOpen]);

  // Switch to a different camera device (only when user explicitly picks one)
  useEffect(() => {
    if (!isOpen || !selectedDeviceId) return;

    // Don't re-init if the active track already matches this device
    const activeTrack = streamRef.current?.getVideoTracks()[0];
    const currentDevice = activeTrack?.getSettings()?.deviceId;
    if (currentDevice === selectedDeviceId) return;

    // Stop existing stream and start new one for the chosen device
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    navigator.mediaDevices
      .getUserMedia({
        video: { deviceId: { exact: selectedDeviceId }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => {
        console.error("Camera switch failed:", err);
      });
  }, [selectedDeviceId]);

  // Handle detection loop
  useEffect(() => {
    if (mode === "stream" && isOpen) {
      if (detectIntervalRef.current) clearInterval(detectIntervalRef.current);
      performLiveDetection();
      detectIntervalRef.current = setInterval(performLiveDetection, 1500);
    } else {
      if (detectIntervalRef.current) {
        clearInterval(detectIntervalRef.current);
        detectIntervalRef.current = null;
      }
      setDetectedObjects([]);
    }

    return () => {
      if (detectIntervalRef.current) {
        clearInterval(detectIntervalRef.current);
        detectIntervalRef.current = null;
      }
    };
  }, [mode, isOpen]);


  const handleCaptureSnapshot = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (ctx) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            onCapture(blob);
          }
        },
        "image/jpeg",
        0.9
      );
    }
  };

  const performLiveDetection = () => {
    if (!videoRef.current || !canvasRef.current || isDetecting) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    if (ctx) {
      canvas.width = 480;
      canvas.height = (video.videoHeight / video.videoWidth) * 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            setIsDetecting(true);
            setStreamError("");
            detectObjects(blob)
              .then((res) => {
                setDetectedObjects(res.objects || []);
              })
              .catch((err) => {
                console.error("YOLO Live Stream detection error:", err);
                if (err.message && err.message.includes("429")) {
                  setStreamError("YOLO server busy.");
                }
              })
              .finally(() => {
                setIsDetecting(false);
              });
          }
        },
        "image/jpeg",
        0.75
      );
    }
  };

  const handleBoxClick = (_obj: DetectedObject) => {
    handleCaptureSnapshot();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md transition-opacity duration-300">
      <div className="relative flex h-full w-full max-w-4xl flex-col bg-app p-4 shadow-2xl sm:h-[85vh] sm:rounded-3xl border border-theme overflow-hidden text-primary">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-theme pb-3">
          <div className="flex items-center gap-3">
            <span
              className="flex h-3 w-3 rounded-full animate-pulse"
              style={{
                backgroundColor: mode === "stream" ? "var(--cyan)" : "var(--accent)",
              }}
            />
            <h2 className="font-display text-lg font-bold tracking-wide">
              {mode === "stream" ? "NeuralLens AR Stream" : "Camera Lens"}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Mode Switcher */}
            <div className="flex rounded-xl bg-muted p-1 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setMode("snapshot")}
                className={`rounded-lg px-3 py-1.5 transition ${
                  mode === "snapshot"
                    ? "bg-elevated shadow text-primary"
                    : "text-muted hover:text-primary"
                }`}
              >
                Snapshot
              </button>
              <button
                type="button"
                onClick={() => setMode("stream")}
                className={`rounded-lg px-3 py-1.5 transition ${
                  mode === "stream"
                    ? "bg-cyan-soft text-cyan shadow"
                    : "text-muted hover:text-cyan"
                }`}
                style={{
                  color: mode === "stream" ? "var(--cyan)" : undefined,
                  background: mode === "stream" ? "var(--cyan-soft)" : undefined,
                }}
              >
                Live AR
              </button>
            </div>

            {/* Device Dropdown */}
            {devices.length > 1 && (
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="rounded-xl border border-theme bg-elevated px-2 py-1 text-xs text-primary outline-none"
              >
                {devices.map((device, i) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${i + 1}`}
                  </option>
                ))}
              </select>
            )}

            {/* Close */}
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-muted transition hover:bg-muted hover:text-primary"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Viewport */}
        <div className="relative flex flex-1 items-center justify-center bg-black/90 p-1 sm:rounded-2xl mt-4 overflow-hidden">
          {permissionError ? (
            <div className="text-center p-6 space-y-4">
              <svg className="mx-auto h-12 w-12 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-sm font-medium text-error">{permissionError}</p>
            </div>
          ) : (
            <div className="relative max-h-full max-w-full overflow-hidden flex items-center justify-center">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-contain max-h-[55vh] sm:max-h-[60vh] rounded-xl"
              />

              {/* Bounding Box HUD Overlays */}
              {mode === "stream" && (
                <div className="absolute inset-0 z-10 pointer-events-none">
                  {detectedObjects.map((obj, i) => {
                    const x = obj.box.xmin / 10;
                    const y = obj.box.ymin / 10;
                    const w = (obj.box.xmax - obj.box.xmin) / 10;
                    const h = (obj.box.ymax - obj.box.ymin) / 10;

                    return (
                      <div
                        key={i}
                        className="absolute border-2 border-cyan-400 group pointer-events-auto cursor-pointer transition-all"
                        style={{
                          left: `${x}%`,
                          top: `${y}%`,
                          width: `${w}%`,
                          height: `${h}%`,
                          borderColor: "var(--cyan)",
                          boxShadow: "0 0 12px var(--cyan-soft)",
                        }}
                        onClick={() => handleBoxClick(obj)}
                        title={`Click to analyze ${obj.label}`}
                      >
                        <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-white" />
                        <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-white" />
                        <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-white" />
                        <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-white" />

                        <div
                          className="absolute -top-6 left-0 rounded px-1.5 py-0.5 text-2xs font-bold text-white shadow-md flex items-center gap-1 select-none whitespace-nowrap animate-fade-in"
                          style={{ background: "var(--cyan)" }}
                        >
                          <span>{obj.label.toUpperCase()}</span>
                          <span className="opacity-75">{Math.round(obj.confidence * 100)}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {mode === "snapshot" && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="h-48 w-48 border-2 border-dashed border-accent opacity-45 rounded-2xl animate-pulse" />
                </div>
              )}

              {isSearching && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm z-20">
                  <div className="loading-dot inline-block h-2.5 w-2.5 rounded-full bg-accent mb-2 animate-bounce" />
                  <p className="text-sm font-semibold text-white">Running Vision Pipeline...</p>
                </div>
              )}

              {streamError && (
                <div className="absolute bottom-4 left-4 right-4 rounded-xl bg-black/85 px-4 py-2 border border-error/20 flex items-center gap-2 text-xs text-error animate-fade-up z-20">
                  <span className="h-2 w-2 rounded-full bg-error" />
                  <span>{streamError} - local YOLO models active</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer controls */}
        <div className="mt-4 flex items-center justify-between">
          <div className="text-2xs text-muted max-w-[60%] leading-snug">
            {mode === "stream" ? (
              <p>AR Lens performs localized YOLO scans. Click active boxes to search immediately.</p>
            ) : (
              <p>Position the product in frame and take a photo to initiate search analysis.</p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              Cancel
            </button>
            {mode === "snapshot" && !permissionError && (
              <button
                onClick={handleCaptureSnapshot}
                disabled={isSearching}
                className="flex items-center gap-2 btn-primary rounded-xl px-5 py-2.5 text-sm font-medium shadow-lg"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <circle cx="12" cy="12" r="3" fill="currentColor" />
                </svg>
                Capture Photo
              </button>
            )}
          </div>
        </div>

        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  );
}
