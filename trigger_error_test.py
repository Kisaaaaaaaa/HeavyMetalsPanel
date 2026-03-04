#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触发analyze页面500错误的测试脚本
"""

import requests
import time

def trigger_analyze_error():
    """尝试触发analyze页面的500错误"""
    base_url = "http://127.0.0.1:5000"
    
    print("正在尝试触发analyze页面的500错误...")
    
    # 等待服务器启动
    time.sleep(3)
    
    try:
        # 测试1: 直接访问analyze页面
        print("测试1: 直接访问analyze页面")
        response = requests.get(f"{base_url}/analyze", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 500:
            print("❌ 发现500错误！")
            print(f"错误内容: {response.text}")
            return True
        
        # 测试2: 登录后访问analyze页面
        print("\n测试2: 登录后访问analyze页面")
        login_data = {
            'username': 'test',
            'password': 'test'
        }
        login_response = requests.post(base_url, data=login_data, timeout=10)
        
        if login_response.status_code == 200:
            cookies = login_response.cookies
            analyze_response = requests.get(f"{base_url}/analyze", cookies=cookies, timeout=10)
            print(f"状态码: {analyze_response.status_code}")
            if analyze_response.status_code == 500:
                print("❌ 发现500错误！")
                print(f"错误内容: {analyze_response.text}")
                return True
        
        # 测试3: 使用无效的session访问
        print("\n测试3: 使用无效的session访问")
        invalid_cookies = {'session': 'invalid_session_data'}
        analyze_response = requests.get(f"{base_url}/analyze", cookies=invalid_cookies, timeout=10)
        print(f"状态码: {analyze_response.status_code}")
        if analyze_response.status_code == 500:
            print("❌ 发现500错误！")
            print(f"错误内容: {analyze_response.text}")
            return True
        
        # 测试4: 多次快速访问
        print("\n测试4: 多次快速访问")
        for i in range(5):
            response = requests.get(f"{base_url}/analyze", timeout=5)
            print(f"第{i+1}次访问状态码: {response.status_code}")
            if response.status_code == 500:
                print("❌ 发现500错误！")
                print(f"错误内容: {response.text}")
                return True
            time.sleep(0.1)
        
        print("\n✅ 所有测试都返回正常状态码，未发现500错误")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("触发Analyze页面500错误测试")
    print("=" * 60)
    
    error_found = trigger_analyze_error()
    
    if error_found:
        print("\n⚠️ 发现了500错误，请检查Flask应用的错误日志")
    else:
        print("\n🎉 未发现500错误，analyze页面工作正常")
        print("\n如果浏览器仍然显示500错误，可能的原因:")
        print("1. 浏览器缓存问题")
        print("2. 浏览器Cookie问题") 
        print("3. 浏览器JavaScript错误")
        print("4. 网络连接问题")
        print("5. 浏览器与服务器的会话问题")
    
    return not error_found

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
