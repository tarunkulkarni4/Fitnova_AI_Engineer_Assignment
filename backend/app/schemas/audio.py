from pydantic import BaseModel, Field

class AudioMetadataResponse(BaseModel):
    duration: float = Field(..., description="Duration of the audio file in seconds")
    sample_rate: int = Field(..., description="Sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    bitrate: int = Field(..., description="Bitrate in bps")
    format: str = Field(..., description="Format extension")
    size: int = Field(..., description="Processed file size in bytes")
    processed_file: str = Field(..., description="Path to the processed WAV file")

    model_config = {
        "json_schema_extra": {
            "example": {
                "duration": 312.45,
                "sample_rate": 16000,
                "channels": 1,
                "bitrate": 256000,
                "format": "wav",
                "size": 10002144,
                "processed_file": "/app/storage/audio/processed/abc123xyz.wav"
            }
        }
    }

class ProcessAudioResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the processing succeeded")
    message: str = Field(..., description="Informative status message")
    metadata: AudioMetadataResponse = Field(..., description="Extracted audio metadata details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Audio processed successfully.",
                "metadata": {
                    "duration": 312,
                    "sample_rate": 16000,
                    "channels": 1,
                    "bitrate": 128000,
                    "format": "wav",
                    "size": 10002144,
                    "processed_file": "/app/storage/audio/processed/abc123xyz.wav"
                }
            }
        }
    }
