package com.moneyops.documents.storage;

import com.google.cloud.storage.BlobInfo;
import com.google.cloud.storage.HttpMethod;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageException;
import com.google.cloud.storage.StorageOptions;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

@Component
@RequiredArgsConstructor
public class FirebaseStorageHelper {

    @Value("${FIREBASE_STORAGE_BUCKET:}")
    private String bucketName;

    @Value("${FIREBASE_SIGNED_URL_TTL_MINUTES:30}")
    private long signedUrlTtlMinutes;

    public UploadResult upload(String orgId, String documentId, MultipartFile file) {
        if (bucketName == null || bucketName.isBlank()) {
            throw new IllegalStateException("FIREBASE_STORAGE_BUCKET is not configured");
        }

        String originalName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document";
        String safeName = originalName.replaceAll("[^a-zA-Z0-9._-]", "_");
        String firebasePath = "organizations/" + orgId + "/documents/" + documentId + "/" + safeName;

        try {
            Storage storage = storage();
            BlobInfo blobInfo = BlobInfo.newBuilder(bucketName, firebasePath)
                    .setContentType(file.getContentType())
                    .build();
            storage.create(blobInfo, file.getBytes());

            return new UploadResult(firebasePath, generateSignedUrl(firebasePath));
        } catch (IOException exception) {
            throw new RuntimeException("Failed to read uploaded file", exception);
        } catch (StorageException exception) {
            throw new RuntimeException("Failed to upload file to Firebase Storage", exception);
        }
    }

    public String generateSignedUrl(String firebasePath) {
        if (bucketName == null || bucketName.isBlank()) {
            throw new IllegalStateException("FIREBASE_STORAGE_BUCKET is not configured");
        }

        try {
            Storage storage = storage();
            BlobInfo blobInfo = BlobInfo.newBuilder(bucketName, firebasePath).build();
            return storage.signUrl(
                            blobInfo,
                            signedUrlTtlMinutes,
                            TimeUnit.MINUTES,
                            Storage.SignUrlOption.httpMethod(HttpMethod.GET),
                            Storage.SignUrlOption.withV4Signature()
                    )
                    .toString();
        } catch (Exception exception) {
            // Fallback to a deterministic storage URL if signed URL generation is unavailable.
            String encodedPath = URLEncoder.encode(firebasePath, StandardCharsets.UTF_8)
                    .replace("+", "%20");
            return "https://firebasestorage.googleapis.com/v0/b/"
                    + bucketName
                    + "/o/"
                    + encodedPath
                    + "?alt=media";
        }
    }

    private Storage storage() {
        return StorageOptions.getDefaultInstance().getService();
    }

    public record UploadResult(String firebasePath, String downloadUrl) {
    }
}
