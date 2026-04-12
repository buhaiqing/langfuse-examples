# Best Practices

> **Purpose**: Comprehensive best practices guide  
> **Last Updated**: 2026-04-08

---

## Instrumentation Best Practices

1. **Always Use Session Context**
   - ✅ Ensure every trace has session_id and user_id
   - ✅ Use contextvars for automatic propagation
   - ❌ Never hardcode session IDs

2. **Attach Prompt Version Metadata**
   - ✅ Version all prompts explicitly
   - ✅ Include prompt_id alongside version
   - ❌ Never skip version tracking

3. **Handle Errors Gracefully**
   - ✅ Let Langfuse capture exceptions automatically
   - ✅ Add custom error metadata when needed
   - ❌ Don't suppress exceptions for tracing

4. **Balance Granularity vs Overhead**
   - ✅ One span per logical operation
   - ✅ Max 3-4 nesting levels
   - ❌ Avoid over-instrumentation

## Performance Best Practices

1. **Minimize Synchronous Overhead**
   - ✅ Use background flush for batch ingestion
   - ✅ Langfuse SDK is async-friendly
   - ❌ Never block on trace submission

2. **Optimize Trace Size**
   - ✅ Avoid payloads >10KB
   - ✅ Truncate large strings
   - ❌ Never log entire request/response bodies

3. **Configure Sampling**
   - ✅ Default: 100% for critical paths
   - ✅ Consider sampling for high-volume paths
   - ❌ Never sample below 10%

## Security Best Practices

1. **Protect Sensitive Data**
   - ✅ Redact PII before logging
   - ✅ Use environment variables for API keys
   - ❌ Never log passwords or credentials

2. **Secure API Keys**
   - ✅ Never commit keys to git
   - ✅ Rotate keys periodically
   - ❌ Never use same key for dev/prod

3. **Data Retention**
   - ✅ Configure retention policies
   - ✅ Delete traces after retention period
   - ❌ Never keep traces indefinitely

---

**Related Documentation**: [Integration Patterns](integration-patterns.md) | [Security Guide](security-guide.md)
