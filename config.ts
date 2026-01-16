// API Configuration
// NOTE: RSA Private keys are excluded for client-side security.
// Gemini API Key is retrieved from process.env.API_KEY per standard.

export const CONFIG = {
    // Agent 2: Scout
    GROQ_API_KEY: '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',
    
    // Agent 10: Historian
    SUPABASE_URL: 'https://db.sbxiiwvkiqmmmmdlqaev.supabase.co',
    SUPABASE_KEY: 'sb_publishable_5PtMghlyPMhL_agZUMPSNg_GFP9rOA7',
    
    // Agent 1/7/8: Kalshi Environments
    KALSHI: {
        PROD_API: 'https://api.elections.kalshi.com/trade-api/v2', 
        SANDBOX_API: 'https://demo-api.kalshi.com/trade-api/v2', // Corrected from .co to .com
        KEY_ID: '41140fda-7f4e-4f77-935f-407e978bdc55',
        PRIVATE_KEY: `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAycSQ1npJ8magnMxx6ttGo9XzDgl2rIj+1e+NB9grOp48zB9i
tHBPXidO+QZ4WWo1bdvAY7bwkqGfa6zxO+gEdb0puC6mAsz/idJtdgs8dvyV6aYd
SWEh069FC7v3YLmGAvZxZ3BiEYiqrE7IfhUh6qZmsMpyynJT1v03AlzzBA+vadf9
652nR7HtD8jltMg986v8ABWeDHmptGdqcTDFsxSqxruOuLX4djvmghBNElVsZiLu
N73G44NF11XAHRIFyBGGE/xVaYzqAUKGBcuHDlcJIubEPb83wbf8ILjmY7XO30lz
SC7glcqoO3dEpOjHBNI5dZNlLSka4oc33jep5wIDAQABAoIBAAEQLBiKjxaGkT9s
7wdnHbmB8xnr1YLrOzcytUeJTWZYVxxW6Ko9Z+2oagjIjpx0rCYRYQjQJKG2gE83
m2h5Zyyc++Sgj6IMJSc7bfWP8ZhJlHClaMTDjO4Un68uz7WOxLSsn8Rabz8wZ9XT
RHMwS/wfNwNPeHNgpC3J1R8KEQMVylg0fJpxoA08IgxCo8BZm1S5iByiNknZP7lr
hneeNfUqiXBPeB1T4eV++90/rIkeaYuJzB7X+QIEhcHIWJzZbGULP50q7iN93KwO
Z2soFVopvJFnS6VVPh2hc65hWEpgSZlJlk+Tx3Mri1/DEsUVKEZ5w55ZTVaoEG6Q
RkdUmeECgYEA3oo+oDhI84n9QuhA5t2iOhTqGVKgG1wkxeP3hn0Xe2hhTyTVJDdq
+LRP/k0voptzZHyzOpPoadKFUImAD7z1fsugei4PHeJbOKQ22q/RkUNgllef8R7F
Hp6NVHwvMwCLo1p9D0xQ0EwuPIJClgsku4/lEDE0ROHZG7A/ZUjXpRMCgYEA6BrI
NffbQPD3a5ezeicxH8tWhClD5nlSvEadcPGei/08yzCMJ7C9Pf6M/8GTPCmT8rKS
jJ3VeT5QKfVLgwKt5AuIR+IQU2KfSSVkBxcWPz9IcHdcx8hTduJAanw9lu4aX7nJ
uRzpqEtYT5LR8LV+1lq0QeTNEnyukn/XgdN8xl0CgYEApnYGTlaLyxAGz4tnMMnM
VWHbkkGJ3a1ZHGVfe8wKSpdTYp4MiOCjNZG63F/kJ9/buujEMCb/DFkau5l+n0ca
41NxoLLfP91XmtDK713ghqY9k3fL/dKkZDj5Qp75t07LJM/FCDJvqL+zPjO5lv6S
5XHHSAtmK7g8bEezxBFurN0CgYB/FSLoAbSHoyglPeNkD49jFCdjp2BpEaaONa/A
hlrD1TzzF7q1hJypE/XJlwhxmWZLLSD2YvjeMJMd1hOpQM9LHFFa4lkD/uyt1Q4m
n6prqM+V3JTtQi8I2aphY3Mpb2b7YLMlasI4hkBtGTtfq1AuN22Y4pix9Zhz2BF8
IPqhdQKBgQCuJ5KKLjjXHc6/UdijniC1aQsP1Eql6TsYku4UD50fRMFtF2FTptk9
wZZ7BOrb1UcSsOnmGkeMMR1XrbnYuRLHqvU/JUdVVbnxVcG0JSVqh5lXHQgkNUlt
0+vpQ4WAEZTGJRZ7CbxHCZeQHI3aokIVHQQ2E+uQ8jE0VMhMzuJUgQ==
-----END RSA PRIVATE KEY-----`
    },
    
    // Agent 3: Signal Interceptor
    RAPID_API_KEY: '379b9cd0ccmshdebb9b9fbf7ddc9p1dc678jsnfcdac3d8081a'
};