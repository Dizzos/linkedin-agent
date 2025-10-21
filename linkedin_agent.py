import anthropic
import os
import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import feedparser
from collections import Counter

class LinkedInAgent:
    """
    LinkedIn агент с Claude и БЕСПЛАТНЫМ мониторингом трендов
    """
    
    def __init__(self, anthropic_api_key: str, linkedin_access_token: str, 
                 industry: str = "технологии", target_audience: str = ""):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.linkedin_token = linkedin_access_token
        self.conversation_history = []
        self.industry = industry
        self.target_audience = target_audience
        
        # RSS фиды по индустриям (бесплатно!)
        self.rss_feeds = {
            "product_management": [
                "https://www.mindtheproduct.com/feed/",
                "https://medium.com/feed/@ProductCoalition",
                "https://www.producttalk.org/feed/",
                "https://www.intercom.com/blog/feed/",
                "https://www.lennysnewsletter.com/feed",
            ],
            "технологии": [
                "https://techcrunch.com/feed/",
                "https://www.theverge.com/rss/index.xml",
                "https://news.ycombinator.com/rss",
                "https://arstechnica.com/feed/",
            ],
            "маркетинг": [
                "https://www.searchenginejournal.com/feed/",
                "https://moz.com/blog/feed",
                "https://contentmarketinginstitute.com/feed/",
            ],
            "startup": [
                "https://news.ycombinator.com/rss",
                "https://techcrunch.com/category/startups/feed/",
                "https://www.reddit.com/r/startups/.rss",
            ],
            "ai": [
                "https://news.ycombinator.com/rss",
                "https://www.reddit.com/r/artificial/.rss",
                "https://www.reddit.com/r/MachineLearning/.rss",
            ]
        }
        
        # Релевантные subreddits для продакт менеджеров
        self.product_subreddits = [
            "ProductManagement",
            "product_design", 
            "startups",
            "SaaS",
            "userexperience",
            "analytics"
        ]
        
        self.tools = [
            {
                "name": "create_linkedin_post",
                "description": "Создает и публикует пост в LinkedIn",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "visibility": {
                            "type": "string",
                            "enum": ["PUBLIC", "CONNECTIONS"],
                            "default": "PUBLIC"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "get_product_trends",
                "description": "ЛУЧШИЙ ВЫБОР для продакт аудитории! Получает агрегированные тренды из всех product-специфичных источников: Mind the Product, r/ProductManagement, r/SaaS, r/startups, Hacker News. Используй это первым делом!",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "web_search_trends",
                "description": "Ищет актуальные темы через веб-поиск. БЕСПЛАТНО через Claude web_search.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос для поиска трендов"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "parse_rss_feeds",
                "description": "Парсит RSS фиды для поиска актуальных новостей. Используй 'product_management' для PM контента.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "industry": {
                            "type": "string",
                            "description": "Индустрия для парсинга фидов: product_management, технологии, startup"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимум новостей",
                            "default": 10
                        }
                    },
                    "required": ["industry"]
                }
            },
            {
                "name": "get_hackernews_trends",
                "description": "Получает trending топики с Hacker News. БЕСПЛАТНО через API.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Количество топиков",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "get_reddit_trends",
                "description": "Получает популярные обсуждения с Reddit. Для PM используй: ProductManagement, product_design, SaaS, startups",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subreddit": {
                            "type": "string",
                            "description": "Название subreddit (ProductManagement, product_design, SaaS, startups)"
                        },
                        "time_filter": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "default": "week"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    },
                    "required": ["subreddit"]
                }
            },
            {
                "name": "analyze_trending_keywords",
                "description": "Анализирует ключевые слова из собранных трендов",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sources_data": {
                            "type": "string",
                            "description": "JSON с данными из разных источников"
                        }
                    },
                    "required": ["sources_data"]
                }
            },
            {
                "name": "validate_topic_relevance",
                "description": "Проверяет актуальность темы для продакт аудитории",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "audience": {"type": "string"}
                    },
                    "required": ["topic"]
                }
            }
        ]
    
    def web_search_trends(self, query: str) -> Dict[str, Any]:
        """
        Использует встроенный web_search от Claude для поиска трендов
        БЕСПЛАТНО - это встроенный инструмент Claude
        """
        return {
            "success": True,
            "query": query,
            "instruction": "use_claude_web_search",
            "message": f"Используй встроенный web_search для запроса: {query}"
        }
    
    def parse_rss_feeds(self, industry: str, limit: int = 10) -> Dict[str, Any]:
        """
        Парсит RSS фиды - ПОЛНОСТЬЮ БЕСПЛАТНО
        """
        feeds = self.rss_feeds.get(industry.lower(), self.rss_feeds.get("технологии", []))
        
        all_articles = []
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    published = entry.get('published_parsed', None)
                    if published:
                        pub_date = datetime(*published[:6])
                    else:
                        pub_date = datetime.now()
                    
                    all_articles.append({
                        "title": entry.get('title', ''),
                        "link": entry.get('link', ''),
                        "summary": entry.get('summary', '')[:200],
                        "published": pub_date.strftime("%Y-%m-%d"),
                        "source": feed.feed.get('title', 'Unknown')
                    })
            except Exception as e:
                print(f"Ошибка парсинга {feed_url}: {e}")
                continue
        
        all_articles.sort(key=lambda x: x['published'], reverse=True)
        
        return {
            "success": True,
            "industry": industry,
            "articles": all_articles[:limit],
            "total": len(all_articles)
        }
    
    def get_hackernews_trends(self, limit: int = 10) -> Dict[str, Any]:
        """
        Получает топовые темы с Hacker News - БЕСПЛАТНО
        """
        try:
            top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(top_stories_url, timeout=10)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            stories = []
            for story_id in story_ids:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                story_response = requests.get(story_url, timeout=5)
                if story_response.ok:
                    story = story_response.json()
                    stories.append({
                        "title": story.get('title', ''),
                        "url": story.get('url', ''),
                        "score": story.get('score', 0),
                        "comments": story.get('descendants', 0)
                    })
            
            return {
                "success": True,
                "source": "Hacker News",
                "stories": stories,
                "total": len(stories)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_reddit_trends(self, subreddit: str, time_filter: str = "week", 
                         limit: int = 10) -> Dict[str, Any]:
        """
        Получает популярные посты с Reddit - БЕСПЛАТНО
        """
        try:
            url = f"https://www.reddit.com/r/{subreddit}/top.json"
            params = {
                "t": time_filter,
                "limit": limit
            }
            headers = {
                "User-Agent": "LinkedInAgent/1.0"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            posts = []
            for post in data['data']['children']:
                post_data = post['data']
                posts.append({
                    "title": post_data.get('title', ''),
                    "score": post_data.get('score', 0),
                    "comments": post_data.get('num_comments', 0),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "created": datetime.fromtimestamp(
                        post_data.get('created_utc', 0)
                    ).strftime("%Y-%m-%d")
                })
            
            return {
                "success": True,
                "subreddit": subreddit,
                "posts": posts,
                "total": len(posts)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_product_trends(self) -> Dict[str, Any]:
        """
        Специализированный метод для получения трендов для продакт аудитории
        """
        all_trends = {
            "rss_articles": [],
            "reddit_discussions": [],
            "hn_stories": []
        }
        
        # 1. Product RSS фиды
        rss_result = self.parse_rss_feeds("product_management", limit=10)
        if rss_result.get("success"):
            all_trends["rss_articles"] = rss_result.get("articles", [])
        
        # 2. Product subreddits
        for subreddit in self.product_subreddits[:3]:
            reddit_result = self.get_reddit_trends(subreddit, "week", 5)
            if reddit_result.get("success"):
                for post in reddit_result.get("posts", []):
                    post["subreddit"] = subreddit
                    all_trends["reddit_discussions"].append(post)
        
        # 3. Hacker News
        hn_result = self.get_hackernews_trends(10)
        if hn_result.get("success"):
            all_trends["hn_stories"] = hn_result.get("stories", [])
        
        # Анализируем ключевые слова
        keywords_result = self.analyze_trending_keywords(json.dumps(all_trends))
        
        return {
            "success": True,
            "sources": {
                "rss_count": len(all_trends["rss_articles"]),
                "reddit_count": len(all_trends["reddit_discussions"]),
                "hn_count": len(all_trends["hn_stories"])
            },
            "data": all_trends,
            "trending_keywords": keywords_result.get("top_keywords", []),
            "summary": "Данные собраны из product-специфичных источников"
        }
    
    def analyze_trending_keywords(self, sources_data: str) -> Dict[str, Any]:
        """
        Анализирует ключевые слова из разных источников
        """
        try:
            data = json.loads(sources_data)
            
            all_text = []
            for source in data.values():
                if isinstance(source, list):
                    for item in source:
                        if isinstance(item, dict):
                            all_text.append(item.get('title', ''))
                            all_text.append(item.get('summary', ''))
            
            words = []
            for text in all_text:
                if text:
                    words.extend([
                        w.lower() for w in text.split() 
                        if len(w) > 4 and w.isalpha()
                    ])
            
            word_freq = Counter(words).most_common(10)
            
            return {
                "success": True,
                "top_keywords": [{"word": w, "count": c} for w, c in word_freq],
                "total_sources": len(data)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_topic_relevance(self, topic: str, audience: str = None) -> Dict[str, Any]:
        """
        Проверяет актуальность темы
        """
        if audience is None:
            audience = self.target_audience
        
        relevance_score = 75
        
        fresh_keywords = ["2025", "2024", "новый", "latest", "breakthrough", "trend", "сегодня"]
        if any(kw in topic.lower() for kw in fresh_keywords):
            relevance_score += 15
        
        if self.industry.lower() in topic.lower():
            relevance_score += 10
        
        is_relevant = relevance_score >= 70
        
        return {
            "success": True,
            "topic": topic,
            "relevance_score": min(relevance_score, 100),
            "is_relevant": is_relevant,
            "recommendation": "✅ Актуально" if is_relevant else "❌ Низкая актуальность"
        }
    
    def create_linkedin_post(self, content: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        """
        Публикует пост в LinkedIn
        """
        user_info_url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {self.linkedin_token}",
            "Content-Type": "application/json"
        }
        
        try:
            user_response = requests.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
            user_id = user_data.get('sub')
            
            post_url = "https://api.linkedin.com/v2/ugcPosts"
            post_data = {
                "author": f"urn:li:person:{user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }
            
            response = requests.post(post_url, headers=headers, json=post_data)
            response.raise_for_status()
            
            return {
                "success": True,
                "post_id": response.json().get('id'),
                "message": "✅ Пост успешно опубликован!"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "❌ Ошибка при публикации"
            }
    
    def process_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает вызовы инструментов
        """
        tool_map = {
            "create_linkedin_post": self.create_linkedin_post,
            "get_product_trends": self.get_product_trends,
            "web_search_trends": self.web_search_trends,
            "parse_rss_feeds": self.parse_rss_feeds,
            "get_hackernews_trends": self.get_hackernews_trends,
            "get_reddit_trends": self.get_reddit_trends,
            "analyze_trending_keywords": self.analyze_trending_keywords,
            "validate_topic_relevance": self.validate_topic_relevance
        }
        
        if tool_name in tool_map:
            return tool_map[tool_name](**tool_input)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    def chat(self, user_message: str) -> str:
    """
    Основной метод взаимодействия, корректно обрабатывает tool_use/tool_result пары
    """
    self.conversation_history.append({
        "role": "user",
        "content": user_message
    })

    system_prompt = f"""Ты - профессиональный LinkedIn Content Manager для ПРОДАКТ АУДИТОРИИ с бесплатным мониторингом трендов.

Индустрия: {self.industry}
🎯 ЦЕЛЕВАЯ АУДИТОРИЯ: {self.target_audience or "Product Managers, Directors of Product, Product Leads"}
- 80% продакт менеджеры, директора продуктов, продакт лиды
- Senior level профессионалы
- Интересуются: стратегия, метрики, frameworks, кейсы, команда

📊 ПРОДАКТ-СПЕЦИФИЧНЫЕ ИСТОЧНИКИ:
1. **parse_rss_feeds** с "product_management" - Mind the Product, Product Coalition, Intercom, Lenny's Newsletter
2. **get_reddit_trends** - r/ProductManagement, r/product_design, r/SaaS, r/startups
3. **get_hackernews_trends** - tech и product обсуждения
4. **web_search_trends** - дополнительная верификация

🔥 ПРИОРИТЕТНЫЕ ТЕМЫ ДЛЯ PM АУДИТОРИИ:
- Product strategy & vision
- Product-market fit
- User research & discovery
- Roadmapping & prioritization
- Metrics & analytics (retention, engagement, NPS)
- Product-led growth
- Stakeholder management
- Team leadership
- AI in product development
- Framework'и (RICE, Jobs-to-be-Done, etc.)

WORKFLOW:
1. Мониторь product-специфичные источники (Mind the Product, r/ProductManagement)
2. Ищи темы релевантные для PM (стратегия, метрики, команда)
3. Валидируй через validate_topic_relevance (≥70%)
4. Создавай практичный, actionable контент
5. Публикуй через create_linkedin_post

📝 СТИЛЬ ДЛЯ ПРОДАКТ АУДИТОРИИ:
- **Тон**: Экспертный, но доступный. Практичный, без воды
- **Структура**: 
  * Сильный хук с конкретной проблемой PM
  * Контекст/данные (цифры, исследования)
  * Практические инсайты или framework
  * Actionable takeaway
  * Вопрос для обсуждения
- **Формат**: Короткие абзацы (2-3 строки), bullet points для списков
- **Эмодзи**: Минимально, только для структуры (📊 🎯 ✅)
- **Хэштеги**: #ProductManagement #ProductStrategy #PMTips #ProductLeadership #ProductDevelopment
- **Избегать**: Слишком общих советов, продажного тона, buzzwords без смысла

ПРИМЕРЫ ХОРОШИХ ХУКОВ ДЛЯ PM:
❌ "Хотите улучшить свой продукт?" (слишком общо)
✅ "83% PM не отслеживают эту метрику. А она предсказывает churn." (конкретно + интрига)

❌ "5 советов для продакт менеджеров" (банально)
✅ "Мы потратили 3 месяца на feature, которую никто не использует. Что мы упустили?" (история + боль)

ВАЖНО: 
- Фокус на ПРАКТИЧЕСКИЕ советы, не теорию
- Используй реальные кейсы и данные
- Говори на языке PM (discovery, backlog, stakeholders, churn, activation)
- ВСЕГДА начинай с мониторинга product-специфичных источников!"""

    response = self.client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=system_prompt,
        tools=self.tools,
        messages=self.conversation_history
    )

    # Обрабатываем цепочку инструментов (tool_use/tool_result)
    while response.stop_reason == "tool_use":
        tool_use_blocks = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        for tool_use_block in tool_use_blocks:
            tool_name = tool_use_block.name
            tool_input = tool_use_block.input

            print(f"\n🔧 {tool_name}")
            print(f"📝 {json.dumps(tool_input, ensure_ascii=False, indent=2)}")

            tool_result = self.process_tool_call(tool_name, tool_input)

            print(f"✅ {json.dumps(tool_result, ensure_ascii=False, indent=2)[:200]}...")

            # Вставляем строго парой: assistant (tool_use), user (tool_result)
            self.conversation_history.append({
                "role": "assistant",
                "content": [tool_use_block]
            })
            self.conversation_history.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                }]
            })

            # Новый запрос: после каждой пары tool_use/tool_result
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                tools=self.tools,
                messages=self.conversation_history
            )
            if response.stop_reason != "tool_use":
                break  # если нет нового tool_use, выходим из цикла

    # Формируем финальный текстовый ответ
    final_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_response += block.text

    # Сохраняем в историю (можно не сохранять, если history нужна только для очереди инструментов)
    self.conversation_history.append({
        "role": "assistant",
        "content": response.content
    })

    return final_response
