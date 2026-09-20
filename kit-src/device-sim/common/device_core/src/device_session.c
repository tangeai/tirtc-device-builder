#include "device/device_session.h"

bool device_session_video_enabled(const device_media_config_t *media,
                                  device_service_t service,
                                  device_media_direction_t direction)
{
    if (media == NULL) {
        return false;
    }

    if (direction == DEVICE_MEDIA_UPLINK) {
        return media->video.uplink_enabled;
    }

    if (direction != DEVICE_MEDIA_DOWNLINK || !media->video.downlink_enabled) {
        return false;
    }

    /* H5 never sends video to the device; AI downlink video is out of scope. */
    return service == DEVICE_SERVICE_VOIP || service == DEVICE_SERVICE_CALL;
}
const char *device_service_name(device_service_t service)
{
    switch (service) {
    case DEVICE_SERVICE_H5: return "h5";
    case DEVICE_SERVICE_AI: return "ai";
    case DEVICE_SERVICE_VOIP: return "voip";
    case DEVICE_SERVICE_CALL: return "device-call";
    default: return "unknown";
    }
}

const char *device_session_state_name(device_session_state_t state)
{
    switch (state) {
    case DEVICE_SESSION_OFFLINE: return "offline";
    case DEVICE_SESSION_IDLE: return "idle";
    case DEVICE_SESSION_H5_STREAMING: return "h5-streaming";
    case DEVICE_SESSION_AI_CONNECTING: return "ai-connecting";
    case DEVICE_SESSION_AI_ACTIVE: return "ai-active";
    case DEVICE_SESSION_RINGING: return "ringing";
    case DEVICE_SESSION_CALLING: return "calling";
    case DEVICE_SESSION_IN_CALL: return "in-call";
    case DEVICE_SESSION_RESTORING_H5: return "restoring-h5";
    default: return "unknown";
    }
}
