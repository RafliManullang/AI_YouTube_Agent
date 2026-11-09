import { Config } from "@remotion/cli/config";

// Hasil render lama otomatis ditimpa, dan frame disimpan sebagai JPEG supaya lebih cepat
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
