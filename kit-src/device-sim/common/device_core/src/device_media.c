#include "device/device_media.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static bool fail(char *error, size_t error_size, const char *message)
{
    if (error != NULL && error_size > 0) {
        (void)snprintf(error, error_size, "%s", message);
    }
    return false;
}

void device_media_config_set_defaults(device_media_config_t *config)
{
    if (config == NULL) {
        return;
    }

    config->audio.codec = DEVICE_AUDIO_CODEC_ALAW;
    (void)snprintf(config->audio.asset_path,
                   sizeof(config->audio.asset_path),
                   "%s",
                   "audio_g711a_8khz_mono_20ms_10s_500packets.g711a");
    config->audio.sample_rate_hz = 8000;
    config->audio.channels = 1;
    config->audio.packet_ms = 20;
    config->audio.duration_ms = DEVICE_MEDIA_REFERENCE_DURATION_MS;
    config->audio.packet_count = 500;

    config->video.codec = DEVICE_VIDEO_CODEC_MJPEG;
    (void)snprintf(config->video.asset_path,
                   sizeof(config->video.asset_path),
                   "%s",
                   "video_mjpeg_640x480_8fps_10s_80frames.mjpeg");
    config->video.width = 640;
    config->video.height = 480;
    config->video.camera_rotation = 0;
    config->video.down_video_rotation = 0;
    config->video.aspect_ratio = 4.0 / 3.0;
    config->video.object_fit[0] = '\0';
    config->video.hor_mirror = false;
    config->video.vert_mirror = false;
    config->video.fps = 8;
    config->video.duration_ms = DEVICE_MEDIA_REFERENCE_DURATION_MS;
    config->video.frame_count = 80;
    config->video.uplink_enabled = true;
    config->video.downlink_enabled = true;
}

bool device_media_config_validate(const device_media_config_t *config,
                                  char *error,
                                  size_t error_size)
{
    if (config == NULL) {
        return fail(error, error_size, "media config is null");
    }
    if (error != NULL && error_size > 0) {
        error[0] = '\0';
    }

    if (config->audio.asset_path[0] == '\0') {
        return fail(error, error_size, "audio asset path is empty");
    }
    if (config->audio.channels != 1) {
        return fail(error, error_size, "the reference profile currently requires mono audio");
    }
    if (config->audio.packet_ms != 20 && config->audio.packet_ms != 40) {
        return fail(error, error_size, "the file source supports 20 ms or 40 ms audio packets");
    }
    if (config->audio.duration_ms == 0 ||
        config->audio.duration_ms % config->audio.packet_ms != 0) {
        return fail(error, error_size, "audio duration must contain complete packets");
    }
    if (config->audio.packet_count !=
        config->audio.duration_ms / config->audio.packet_ms) {
        return fail(error, error_size, "audio packet count does not match duration and packet interval");
    }

    switch (config->audio.codec) {
    case DEVICE_AUDIO_CODEC_ALAW:
    case DEVICE_AUDIO_CODEC_OPUS:
        if (config->audio.sample_rate_hz != 8000 &&
            config->audio.sample_rate_hz != 16000) {
            return fail(error, error_size, "alaw/Opus sample rate must be 8000 or 16000 Hz");
        }
        break;
    case DEVICE_AUDIO_CODEC_AMR_NB:
        if (config->audio.sample_rate_hz != 8000) {
            return fail(error, error_size, "AMR-NB sample rate must be 8000 Hz");
        }
        break;
    case DEVICE_AUDIO_CODEC_AMR_WB:
        if (config->audio.sample_rate_hz != 16000) {
            return fail(error, error_size, "AMR-WB sample rate must be 16000 Hz");
        }
        break;
    default:
        return fail(error, error_size, "unknown audio codec");
    }

    if (config->video.uplink_enabled) {
        if (config->video.asset_path[0] == '\0') {
            return fail(error, error_size, "uplink video asset path is empty");
        }
        if (!((config->video.width == 640 && config->video.height == 480) ||
              (config->video.width == 640 && config->video.height == 360) ||
              (config->video.width == 240 && config->video.height == 320))) {
            return fail(error,
                        error_size,
                        "video resolution must be 640x480, 640x360, or 240x320");
        }
        if (config->video.duration_ms != DEVICE_MEDIA_REFERENCE_DURATION_MS) {
            return fail(error, error_size, "the reference video asset must be 10 seconds");
        }
    }
    if (config->video.camera_rotation != 0 &&
        config->video.camera_rotation != 90 &&
        config->video.camera_rotation != 180 &&
        config->video.camera_rotation != 270) {
        return fail(error, error_size, "camera rotation must be 0, 90, 180, or 270");
    }
    if (config->video.down_video_rotation > 2) {
        return fail(error, error_size, "down video rotation must be 0, 1, or 2");
    }
    if (!isfinite(config->video.aspect_ratio) || config->video.aspect_ratio <= 0) {
        return fail(error, error_size, "video aspect ratio must be greater than 0");
    }
    if (config->video.object_fit[0] != '\0' &&
        strcmp(config->video.object_fit, "fill") != 0 &&
        strcmp(config->video.object_fit, "contain") != 0) {
        return fail(error, error_size, "video object fit must be fill or contain");
    }

    switch (config->video.codec) {
    case DEVICE_VIDEO_CODEC_MJPEG:
        if ((config->video.uplink_enabled || config->video.downlink_enabled) &&
            config->video.fps != 8) {
            return fail(error, error_size, "MJPEG reference profile requires 8 fps");
        }
        if (config->video.uplink_enabled && config->video.frame_count != 80U) {
            return fail(error, error_size, "MJPEG 10-second reference asset requires 80 frames");
        }
        break;
    case DEVICE_VIDEO_CODEC_H264:
        if ((config->video.uplink_enabled || config->video.downlink_enabled) &&
            config->video.fps != 15) {
            return fail(error, error_size, "H264 reference profile requires 15 fps");
        }
        if (config->video.uplink_enabled && config->video.frame_count != 150U) {
            return fail(error, error_size, "H264 10-second reference asset requires 150 frames");
        }
        break;
    case DEVICE_VIDEO_CODEC_H265_RESERVED:
        return fail(error, error_size, "H265 is reserved but not implemented");
    default:
        return fail(error, error_size, "unknown video codec");
    }

    return true;
}

const char *device_audio_codec_name(device_audio_codec_t codec)
{
    switch (codec) {
    case DEVICE_AUDIO_CODEC_ALAW: return "alaw";
    case DEVICE_AUDIO_CODEC_AMR_NB: return "amr-nb";
    case DEVICE_AUDIO_CODEC_AMR_WB: return "amr-wb";
    case DEVICE_AUDIO_CODEC_OPUS: return "opus";
    default: return "unknown";
    }
}

bool device_audio_codec_parse(const char *name, device_audio_codec_t *codec)
{
    if (name == NULL || codec == NULL) {
        return false;
    }
    if (strcmp(name, "alaw") == 0 || strcmp(name, "g711a") == 0) {
        *codec = DEVICE_AUDIO_CODEC_ALAW;
    } else if (strcmp(name, "amr-nb") == 0) {
        *codec = DEVICE_AUDIO_CODEC_AMR_NB;
    } else if (strcmp(name, "amr-wb") == 0) {
        *codec = DEVICE_AUDIO_CODEC_AMR_WB;
    } else if (strcmp(name, "opus") == 0) {
        *codec = DEVICE_AUDIO_CODEC_OPUS;
    } else {
        return false;
    }
    return true;
}

const char *device_video_codec_name(device_video_codec_t codec)
{
    switch (codec) {
    case DEVICE_VIDEO_CODEC_MJPEG: return "mjpeg";
    case DEVICE_VIDEO_CODEC_H264: return "h264";
    case DEVICE_VIDEO_CODEC_H265_RESERVED: return "h265-reserved";
    default: return "unknown";
    }
}
