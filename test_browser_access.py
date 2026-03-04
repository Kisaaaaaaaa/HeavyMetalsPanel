#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟浏览器访问analyze页面的测试脚本
"""

import requests
import time
import sys

def test_analyze_page():
    """测试analyze页面访问"""
    print("正在测试analyze页面访问...")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # 首先访问首页
        print("1. 访问首页...")
        response = requests.get(base_url, timeout=10)
        print(f"   状态码: {response.status_code}")
        
        # 尝试登录
        print("2. 尝试登录...")
        login_data = {
            'username': 'testuser',
            'password': 'testpass'
        }
        login_response = requests.post(base_url, data=login_data, timeout=10)
        print(f"   登录状态码: {login_response.status_code}")
        
        # 获取cookies
        cookies = login_response.cookies
        
        # 访问analyze页面
        print("3. 访问analyze页面...")
        analyze_response = requests.get(f"{base_url}/analyze", cookies=cookies, timeout=10)
        print(f"   Analyze页面状态码: {analyze_response.status_code}")
        
        if analyze_response.status_code == 200:
            print("✅ Analyze页面访问成功")
            print(f"   页面内容长度: {len(analyze_response.text)}")
            return True
        else:
            print(f"❌ Analyze页面访问失败: {analyze_response.status_code}")
            print(f"   错误内容: {analyze_response.text[:500]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保Flask应用正在运行")
        return False
    except Exception as e:
        print(f"❌ 访问过程中发生错误: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("模拟浏览器访问Analyze页面测试")
    print("=" * 60)
    
    # 等待一下确保服务器启动
    print("等待服务器启动...")
    time.sleep(2)
    
    success = test_analyze_page()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试通过！Analyze页面可以正常访问")
    else:
        print("⚠️ 测试失败，请检查服务器状态")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
