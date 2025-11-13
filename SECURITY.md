# Security Implementation Guide

This document outlines the comprehensive security measures implemented in the Sokoni Africa API to protect against common attacks and vulnerabilities.

## Security Features Implemented

### 1. Authentication & Authorization

#### Password Security
- **Password Strength Validation**: Passwords must meet the following requirements:
  - Minimum 8 characters, maximum 128 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - Cannot be common passwords (password, 12345678, etc.)
- **Password Hashing**: Uses bcrypt with automatic salt generation
- **Account Lockout**: After 5 failed login attempts, accounts are locked for 15 minutes

#### JWT Tokens
- **Token Expiration**: Access tokens expire after 30 minutes (configurable)
- **Secure Token Generation**: Uses HS256 algorithm with strong secret key
- **Token Validation**: All protected endpoints validate token signature and expiration

### 2. Rate Limiting

Rate limiting is implemented to prevent brute force attacks and DoS:

- **Login Endpoint**: 5 attempts per 5 minutes
- **Registration**: 3 attempts per 10 minutes
- **Password Reset**: 3 attempts per 10 minutes
- **Default**: 100 requests per minute for other endpoints

Rate limits are tracked per IP address or authenticated user.

### 3. Input Validation & Sanitization

- **XSS Prevention**: All user input is sanitized to remove potentially dangerous characters
- **SQL Injection Prevention**: Uses SQLAlchemy ORM with parameterized queries
- **Input Length Limits**: Maximum lengths enforced on all text inputs
- **Type Validation**: Pydantic schemas validate all request data

### 4. Security Headers

The following security headers are added to all responses:

- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables XSS filtering
- `Strict-Transport-Security` - Forces HTTPS (in production)
- `Content-Security-Policy` - Restricts resource loading
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

### 5. CORS Configuration

- **Production**: Only allows specific origins (configured in `.env`)
- **Development**: Allows localhost and private network addresses
- **Credentials**: Only allowed with specific origins
- **Methods**: Explicitly allows only necessary HTTP methods
- **Headers**: Only allows necessary headers

### 6. Request Size Limits

- **Maximum Request Size**: 10 MB
- Prevents DoS attacks through large payloads

### 7. Security Logging

All security-related events are logged:
- Failed login attempts
- Rate limit violations
- Account lockouts
- Slow requests (>5 seconds)
- Authentication errors (401, 403, 429)

### 8. API Documentation Security

- **Production**: API documentation endpoints (`/docs`, `/redoc`) are disabled
- **Development**: Documentation is available for testing

### 9. Database Security

- **SSL/TLS**: Database connections use SSL in production
- **Parameterized Queries**: All database queries use SQLAlchemy ORM
- **Connection Pooling**: Secure connection management

### 10. Error Handling

- **Generic Error Messages**: Prevents information leakage
- **No Stack Traces**: Stack traces are not exposed in production
- **Consistent Error Format**: All errors follow a standard format

## Security Best Practices

### Environment Variables

Never commit sensitive data to version control. Use environment variables:

```env
# Required
SECRET_KEY=your-very-long-random-secret-key-minimum-32-characters
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require

# Security Settings
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong `SECRET_KEY` (minimum 32 characters, random)
- [ ] Configure specific `ALLOWED_ORIGINS` (not "*")
- [ ] Enable SSL/TLS for database connections
- [ ] Use HTTPS for all API endpoints
- [ ] Regularly rotate `SECRET_KEY` (requires re-authentication of all users)
- [ ] Monitor security logs for suspicious activity
- [ ] Keep dependencies updated
- [ ] Use a reverse proxy (nginx) with rate limiting
- [ ] Implement WAF (Web Application Firewall) if possible

### Password Policy

Users must create passwords that:
- Are at least 8 characters long
- Contain uppercase and lowercase letters
- Contain at least one digit
- Are not common passwords

### Account Security

- Accounts are locked after 5 failed login attempts
- Lockout duration: 15 minutes
- Lockout is automatically released after the duration expires

### API Security

- All sensitive endpoints require authentication
- Rate limiting prevents abuse
- Request size limits prevent DoS attacks
- Security headers protect against common web vulnerabilities

## Monitoring & Alerts

### Logs to Monitor

1. **Failed Login Attempts**: Multiple failures from same IP
2. **Rate Limit Violations**: Potential automated attacks
3. **Account Lockouts**: May indicate brute force attempts
4. **Slow Requests**: Potential DoS or performance issues
5. **Authentication Errors**: Invalid tokens or expired sessions

### Recommended Alerts

- Alert when account lockout rate exceeds threshold
- Alert on repeated rate limit violations from same IP
- Alert on unusual authentication patterns
- Alert on slow request patterns

## Security Updates

### Regular Maintenance

1. **Dependency Updates**: Regularly update all Python packages
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   ```

2. **Security Audits**: Run security scanners regularly
   ```bash
   pip install safety
   safety check
   ```

3. **Code Reviews**: Review all code changes for security issues

4. **Penetration Testing**: Regular security testing by professionals

## Incident Response

If a security incident is detected:

1. **Immediate Actions**:
   - Lock affected accounts
   - Revoke all tokens (if necessary)
   - Review security logs

2. **Investigation**:
   - Identify the attack vector
   - Assess data exposure
   - Document the incident

3. **Remediation**:
   - Patch vulnerabilities
   - Update security measures
   - Notify affected users (if required)

4. **Prevention**:
   - Update security policies
   - Improve monitoring
   - Conduct security training

## Additional Security Recommendations

### For Production Deployment

1. **Use a Reverse Proxy** (nginx):
   - Additional rate limiting
   - SSL/TLS termination
   - DDoS protection

2. **Implement WAF** (Web Application Firewall):
   - Cloudflare, AWS WAF, etc.
   - Additional layer of protection

3. **Database Security**:
   - Use read-only database users for queries
   - Implement database-level access controls
   - Regular backups with encryption

4. **Secrets Management**:
   - Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)
   - Never hardcode secrets
   - Rotate secrets regularly

5. **Monitoring & Alerting**:
   - Set up monitoring (Prometheus, Grafana)
   - Configure alerts for security events
   - Regular security audits

## Contact

For security concerns or to report vulnerabilities, please contact the development team.

**Note**: This is a living document and will be updated as new security measures are implemented.

