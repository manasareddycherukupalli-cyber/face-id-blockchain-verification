// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title FaceMatchRegistry
/// @notice Tamper-evident record of a face-verified reverse-image-search match.
///
/// The design separates two jobs:
///
///   - The *event* carries the human-readable match so anyone can read it
///     straight off a block explorer with no off-chain lookup.
///   - The *stored hash* is the integrity anchor: it is the keccak256 of the
///     canonical JSON record held off-chain. Re-hash that file later and compare
///     against `recordedAt` to prove the record has not been altered. That is
///     what makes it tamper-EVIDENT rather than merely tamper-resistant.
///
/// Events cost roughly an order of magnitude less gas than storage, so keeping
/// the payload in the event and only the 32-byte anchor in storage is both the
/// cheaper and the more honest design.
contract FaceMatchRegistry {
    struct Record {
        uint64 timestamp;   // block time when first recorded; 0 means unseen
        address submitter;
    }

    /// @dev recordHash => when and by whom it was anchored.
    mapping(bytes32 => Record) public records;

    uint256 public totalRecords;

    event MatchRecorded(
        bytes32 indexed recordHash,
        address indexed submitter,
        string sourceUrl,          // the matched social media post
        string platform,           // e.g. "instagram.com"
        uint16 similarityBps,      // cosine similarity in basis points, 0..10000
        uint16 thresholdBps,       // the threshold it was judged against
        bytes32 queryImageHash,    // sha256 of the input image bytes
        bytes32 faceEmbeddingHash, // sha256 of the 512-d query embedding
        uint64 timestamp
    );

    error AlreadyRecorded(bytes32 recordHash, uint64 firstSeen);
    error EmptySourceUrl();
    error SimilarityOutOfRange(uint16 similarityBps);

    /// @notice Anchor one verified match.
    /// @dev Reverts on a duplicate rather than silently overwriting - the first
    ///      write is the one that counts, and a re-submission attempt is itself
    ///      information worth surfacing.
    function recordMatch(
        bytes32 recordHash,
        string calldata sourceUrl,
        string calldata platform,
        uint16 similarityBps,
        uint16 thresholdBps,
        bytes32 queryImageHash,
        bytes32 faceEmbeddingHash
    ) external {
        Record storage existing = records[recordHash];
        if (existing.timestamp != 0) {
            revert AlreadyRecorded(recordHash, existing.timestamp);
        }
        if (bytes(sourceUrl).length == 0) revert EmptySourceUrl();
        // Cosine similarity is bounded; anything outside 0..10000 bps means the
        // caller computed it wrong, and a bad number must not become permanent.
        if (similarityBps > 10000) revert SimilarityOutOfRange(similarityBps);

        uint64 ts = uint64(block.timestamp);
        records[recordHash] = Record({timestamp: ts, submitter: msg.sender});
        unchecked { totalRecords++; }

        emit MatchRecorded(
            recordHash,
            msg.sender,
            sourceUrl,
            platform,
            similarityBps,
            thresholdBps,
            queryImageHash,
            faceEmbeddingHash,
            ts
        );
    }

    /// @notice True if this exact record has been anchored before.
    function isRecorded(bytes32 recordHash) external view returns (bool) {
        return records[recordHash].timestamp != 0;
    }
}
